"""Real-time state patch emitter for Fusion 360.

Detects Fusion state changes (selection, timeline, parameters, focus) and
queues them as atomic PATCH dicts.  The LLM pulls patches via
`get_patches_since(t)` to catch up on what changed.

Because Fusion's add-in event model is limited, we combine:
  - Direct event handlers where available (selection)
  - A polling snapshot-diff loop (500ms) for everything else
"""

import time
import threading
import traceback
from typing import Dict, List, Optional, Any

try:
    import adsk.core
    import adsk.fusion
except ImportError:
    pass

MAX_QUEUE = 100
POLL_INTERVAL_SEC = 0.5


class PatchEmitter:
    """Listens to Fusion state changes and emits PATCH dicts."""

    def __init__(self, app, cad_state):
        self.app = app
        self.state = cad_state
        self._queue: List[dict] = []
        self._lock = threading.Lock()
        self._last_snapshot: Optional[dict] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start background polling for state changes."""
        if self._running:
            return
        self._running = True
        self._last_snapshot = self._safe_snapshot()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        """Stop background polling."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

    def get_patches_since(self, since_t: int) -> dict:
        """Return patches newer than since_t."""
        with self._lock:
            patches = [p for p in self._queue if p["t"] > since_t]
        return {
            "patches": patches,
            "current_t": self.state.tick,
            "queued": len(self._queue),
        }

    def drain(self) -> List[dict]:
        """Return all queued patches and clear the queue."""
        with self._lock:
            patches = self._queue[:]
            self._queue.clear()
        return patches

    def emit_manual(self, ops: List[dict]):
        """Manually emit a patch (used by action executor after applying commands)."""
        self._emit_ops(ops)

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------

    def _poll_loop(self):
        """Background thread: periodically snapshot and diff."""
        while self._running:
            try:
                time.sleep(POLL_INTERVAL_SEC)
                if not self._running:
                    break
                current = self._safe_snapshot()
                if current and self._last_snapshot:
                    ops = self._diff(self._last_snapshot, current)
                    if ops:
                        self._emit_ops(ops)
                self._last_snapshot = current
            except Exception:
                pass

    def _safe_snapshot(self) -> Optional[dict]:
        """Take a state snapshot, suppressing errors."""
        try:
            return self.state.snapshot(sparse=False)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Diff engine
    # ------------------------------------------------------------------

    def _diff(self, old: dict, new: dict) -> List[dict]:
        """Compare two STATE snapshots and produce set ops for differences."""
        ops = []
        skip_keys = {"t", "_error"}

        for key in new:
            if key in skip_keys:
                continue
            old_val = old.get(key)
            new_val = new[key]
            if old_val != new_val:
                if isinstance(new_val, dict) and isinstance(old_val, dict):
                    sub_ops = self._diff_dict(key, old_val, new_val)
                    ops.extend(sub_ops)
                else:
                    ops.append({"set": key, "v": new_val})

        return ops

    def _diff_dict(self, prefix: str, old: dict, new: dict) -> List[dict]:
        """Diff nested dicts, producing dotted-path set ops."""
        ops = []
        all_keys = set(list(old.keys()) + list(new.keys()))

        for key in all_keys:
            path = f"{prefix}.{key}"
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val == new_val:
                continue

            if new_val is None and old_val is not None:
                ops.append({"del": path})
            elif isinstance(new_val, dict) and isinstance(old_val, dict):
                ops.extend(self._diff_dict(path, old_val, new_val))
            else:
                ops.append({"set": path, "v": new_val})

        return ops

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def _emit_ops(self, ops: List[dict]):
        """Wrap ops in a PATCH and add to queue."""
        if not ops:
            return
        t = self.state.bump_tick()
        patch = {"t": t, "ops": ops}
        with self._lock:
            self._queue.append(patch)
            while len(self._queue) > MAX_QUEUE:
                self._queue.pop(0)

    # ------------------------------------------------------------------
    # Convenience: emit specific change types
    # ------------------------------------------------------------------

    def emit_selection_change(self, new_sel: List[str]):
        self._emit_ops([{"set": "sel", "v": new_sel}])

    def emit_focus_change(self, new_focus: dict):
        self._emit_ops([{"set": "focus", "v": new_focus}])

    def emit_timeline_change(self, count: int, at: int, rolled_to: Optional[str] = None):
        ops = [
            {"set": "timeline.count", "v": count},
            {"set": "timeline.at", "v": at},
        ]
        if rolled_to is not None:
            ops.append({"set": "timeline.rolled_to", "v": rolled_to})
        self._emit_ops(ops)

    def emit_param_change(self, name: str, value: str):
        self._emit_ops([{"set": f"params.{name}", "v": {"v": value}}])
