"""
Fusion 360 MCP Bridge Add-in — slim orchestrator.

Delegates handlers to domain modules:
  - handlers_sketch        (complete sketch domain — 38 endpoints)
  - handlers_solid         (features, bodies, transforms)
  - handlers_construction  (planes, axes, points, measurements)
  - handlers_camera        (viewport, screenshots, export)
  - handlers_nav           (STATE / PATCH / LOCAL_GRAPH / frames)
  - handlers_timeline      (parametric timeline)
  - handlers_assembly      (components, joints, hierarchy)
  - handlers_cam_setup     (CAM setups, tools, post-processing)
  - handlers_cam_2d        (2D/2.5D milling operations)
  - handlers_cam_3d        (3D surface machining operations)

The HTTP server, custom-event thread marshaling, and lifecycle (run/stop)
live here.  Individual handler logic lives in the domain modules.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import adsk.core
import adsk.fusion
import adsk.cam
import threading
import json
import traceback
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

_LOGFILE = os.path.join(_THIS_DIR, "bridge_error.log")

def _log(msg):
    with open(_LOGFILE, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

_log(f"Module load starting. sys.path[0]={sys.path[0] if sys.path else 'empty'}")
_log(f"__file__={__file__}")
_log(f"cwd={os.getcwd()}")

# Force-reload all bridge modules so stop/start picks up file changes
import importlib as _il
for _mod_name in [k for k in sys.modules if k.startswith(("bridge_helpers", "handlers_", "entity_resolver",
                                                            "frame_manager", "cad_state", "graph_extractor",
                                                            "patch_emitter", "action_executor", "_legacy_handlers"))]:
    try:
        _il.reload(sys.modules[_mod_name])
        _log(f"  reloaded cached module: {_mod_name}")
    except Exception:
        del sys.modules[_mod_name]
        _log(f"  purged stale module: {_mod_name}")

# ── Shared helpers ────────────────────────────────────────────
try:
    from bridge_helpers import set_app, set_frame_manager, set_nav_state
    import bridge_helpers as _bh
    _log("bridge_helpers: OK")
except Exception as e:
    _log(f"bridge_helpers FAIL: {e}\n{traceback.format_exc()}")
    raise

# ── Domain handler modules ────────────────────────────────────
try:
    from handlers_sketch import SKETCH_ROUTES
    _log(f"handlers_sketch: OK ({len(SKETCH_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_sketch FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_solid import SOLID_ROUTES
    _log(f"handlers_solid: OK ({len(SOLID_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_solid FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_construction import CONSTRUCTION_ROUTES
    _log(f"handlers_construction: OK ({len(CONSTRUCTION_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_construction FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_camera import CAMERA_ROUTES
    _log(f"handlers_camera: OK ({len(CAMERA_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_camera FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_nav import NAV_ROUTES
    _log(f"handlers_nav: OK ({len(NAV_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_nav FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_timeline import TIMELINE_ROUTES
    _log(f"handlers_timeline: OK ({len(TIMELINE_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_timeline FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_assembly import ASSEMBLY_ROUTES
    _log(f"handlers_assembly: OK ({len(ASSEMBLY_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_assembly FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_cam_setup import CAM_SETUP_ROUTES
    _log(f"handlers_cam_setup: OK ({len(CAM_SETUP_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_cam_setup FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_cam_2d import CAM_2D_ROUTES
    _log(f"handlers_cam_2d: OK ({len(CAM_2D_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_cam_2d FAIL: {e}\n{traceback.format_exc()}")
    raise

try:
    from handlers_cam_3d import CAM_3D_ROUTES
    _log(f"handlers_cam_3d: OK ({len(CAM_3D_ROUTES)} routes)")
except Exception as e:
    _log(f"handlers_cam_3d FAIL: {e}\n{traceback.format_exc()}")
    raise

# Frame manager + nav state modules (needed for run() initialization)
try:
    from frame_manager import FrameManager
    from entity_resolver import EntityResolver
    from cad_state import CADState
    from graph_extractor import GraphExtractor
    from patch_emitter import PatchEmitter
    from action_executor import ActionExecutor
    _log("nav core modules: OK")
except Exception as e:
    _log(f"nav core FAIL: {e}\n{traceback.format_exc()}")
    raise

# Legacy handlers — everything not yet split into domain modules
try:
    import _legacy_handlers as _lh
    _log("_legacy_handlers: OK")
except Exception as e:
    _log(f"_legacy_handlers FAIL: {e}\n{traceback.format_exc()}")
    raise

_log("All imports done")

# ── Globals ───────────────────────────────────────────────────
app = None
ui = None
server = None
server_thread = None
custom_event = None
custom_event_handler = None
PORT = 8080

# Thread-safety primitives for command dispatch
pending_route = None
pending_body = None
command_result = None
command_ready = threading.Event()


# ── HTTP handler ──────────────────────────────────────────────

class FusionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        global pending_route, pending_body, command_result, command_ready

        path = urlparse(self.path).path
        if path not in ROUTES:
            self.send_json({"error": True, "message": f"Unknown route: {path}"}, 404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}

        command_ready.clear()
        command_result = None
        pending_route = path
        pending_body = body

        try:
            app.fireCustomEvent("FusionMCPCommandEvent")
            if command_ready.wait(timeout=30):
                self.send_json(command_result if command_result else {"error": True, "message": "No result"})
            else:
                self.send_json({"error": True, "message": "Command timed out"})
        except Exception as e:
            self.send_json({"error": True, "message": str(e), "traceback": traceback.format_exc()}, 500)


# ── Custom event handler (runs on Fusion's main thread) ───────

class CommandEventHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        global pending_route, pending_body, command_result, command_ready
        try:
            handler = ROUTES.get(pending_route)
            if handler:
                command_result = handler(pending_body)
            else:
                command_result = {"error": True, "message": f"Route not found: {pending_route}"}
        except Exception as e:
            command_result = {"error": True, "message": str(e), "traceback": traceback.format_exc()}
        finally:
            command_ready.set()


# ── Master route table ────────────────────────────────────────

ROUTES = {}

_HANDLER_MODULES = {
    "handlers_sketch":       ("SKETCH_ROUTES",),
    "handlers_solid":        ("SOLID_ROUTES",),
    "handlers_construction": ("CONSTRUCTION_ROUTES",),
    "handlers_camera":       ("CAMERA_ROUTES",),
    "handlers_nav":          ("NAV_ROUTES",),
    "handlers_timeline":     ("TIMELINE_ROUTES",),
    "handlers_assembly":     ("ASSEMBLY_ROUTES",),
    "handlers_cam_setup":    ("CAM_SETUP_ROUTES",),
    "handlers_cam_2d":       ("CAM_2D_ROUTES",),
    "handlers_cam_3d":       ("CAM_3D_ROUTES",),
}

_SUPPORT_MODULES = [
    "bridge_helpers", "entity_resolver", "frame_manager",
    "cad_state", "graph_extractor", "patch_emitter",
    "action_executor", "_legacy_handlers",
]

def _build_routes():
    """(Re)build the master route table from all handler modules."""
    ROUTES.clear()

    for mod_name, route_names in _HANDLER_MODULES.items():
        mod = sys.modules.get(mod_name)
        if mod:
            for rn in route_names:
                ROUTES.update(getattr(mod, rn, {}))

    # Legacy backward-compat aliases
    if "handlers_timeline" in sys.modules:
        tr = getattr(sys.modules["handlers_timeline"], "TIMELINE_ROUTES", {})
        for old, new in [("/undo", "/timeline_undo"), ("/redo", "/timeline_redo"),
                         ("/get_timeline", "/timeline_list"),
                         ("/get_feature_parameters", "/timeline_feature_params"),
                         ("/edit_feature_parameter", "/timeline_edit_param")]:
            if new in tr:
                ROUTES[old] = tr[new]

    if "handlers_cam_2d" in sys.modules:
        c2 = getattr(sys.modules["handlers_cam_2d"], "CAM_2D_ROUTES", {})
        for old, new in [("/cam_create_2d_contour", "/cam_2d_contour"),
                         ("/cam_create_2d_pocket", "/cam_2d_pocket"),
                         ("/cam_create_engrave", "/cam_2d_engrave"),
                         ("/cam_create_trace", "/cam_2d_trace"),
                         ("/cam_create_face", "/cam_2d_face"),
                         ("/cam_create_contour_advanced", "/cam_2d_contour_advanced"),
                         ("/cam_create_miter_clearing", "/cam_2d_miter_clearing")]:
            if new in c2:
                ROUTES[old] = c2[new]

    if "handlers_cam_setup" in sys.modules:
        cs = getattr(sys.modules["handlers_cam_setup"], "CAM_SETUP_ROUTES", {})
        if "/cam_generate" in cs:
            ROUTES["/cam_generate_all"] = cs["/cam_generate"]

    ROUTES.update({
        "/ping": _lh.handle_ping,
        "/info": _lh.handle_info,
        "/new_document": _lh.handle_new_document,
        "/open_document": _lh.handle_open_document,
        "/save": _lh.handle_save,
        "/get_all_parts": _lh.handle_get_all_parts,
        "/create_parameter": _lh.handle_create_parameter,
        "/modify_parameter": _lh.handle_modify_parameter,
        "/list_parameters": _lh.handle_list_parameters,
        "/list_all_parameters": _lh.handle_list_all_parameters,
        "/apply_appearance": _lh.handle_apply_appearance,
        "/list_appearances": _lh.handle_list_appearances,
        "/switch_workspace": _lh.handle_switch_workspace,
    })

    ROUTES["/reload"] = _handle_reload


def _handle_reload(body):
    """Hot-reload all handler modules and rebuild routes."""
    reloaded = []
    errors = []

    # Capture live state from bridge_helpers BEFORE reload wipes it
    saved = {}
    for attr in ("_app", "frame_manager", "entity_resolver", "cad_state",
                 "graph_extractor", "patch_emitter", "action_executor"):
        saved[attr] = getattr(_bh, attr, None)

    for mod_name in _SUPPORT_MODULES:
        if mod_name in sys.modules:
            try:
                _il.reload(sys.modules[mod_name])
                reloaded.append(mod_name)
            except Exception as e:
                errors.append(f"{mod_name}: {e}")

    for mod_name in _HANDLER_MODULES:
        if mod_name in sys.modules:
            try:
                _il.reload(sys.modules[mod_name])
                reloaded.append(mod_name)
            except Exception as e:
                errors.append(f"{mod_name}: {e}")

    # Re-inject live state into freshly reloaded modules
    _bh.set_app(app or saved.get("_app"))
    fm = saved.get("frame_manager")
    if fm:
        _bh.set_frame_manager(fm)
    er = saved.get("entity_resolver")
    cs = saved.get("cad_state")
    ge = saved.get("graph_extractor")
    pe = saved.get("patch_emitter")
    ae = saved.get("action_executor")
    if er and cs and ge and pe and ae:
        _bh.set_nav_state(er, cs, ge, pe, ae)

    lh = sys.modules.get("_legacy_handlers")
    if lh:
        lh.app = app
        lh.ui = ui
        if fm: lh.frame_manager = fm
        for attr, val in [("entity_resolver", er), ("cad_state", cs),
                          ("graph_extractor", ge), ("patch_emitter", pe),
                          ("action_executor", ae)]:
            if val:
                setattr(lh, attr, val)

    _build_routes()
    return {
        "success": len(errors) == 0,
        "reloaded": reloaded,
        "errors": errors,
        "total_routes": len(ROUTES),
    }

_build_routes()


# ── Server lifecycle ──────────────────────────────────────────

def start_server():
    global server
    try:
        server = HTTPServer(("localhost", PORT), FusionHandler)
        server.serve_forever()
    except Exception as e:
        if ui:
            ui.messageBox(f"Server error: {str(e)}")


def run(context):
    global app, ui, server_thread, custom_event, custom_event_handler

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Push app reference into shared helpers
        set_app(app)
        # Also push into legacy module so its globals work
        _lh.app = app
        _lh.ui = ui

        # Initialize frame manager
        fm = FrameManager()
        set_frame_manager(fm)
        _lh.frame_manager = fm

        # Initialize nav state system
        er = EntityResolver()
        cs = CADState(app, fm, er)
        ge = GraphExtractor(app, er)
        pe = PatchEmitter(app, cs)
        ae = ActionExecutor(app, cs, pe, ROUTES)
        set_nav_state(er, cs, ge, pe, ae)

        # Wire legacy globals
        _lh.entity_resolver = er
        _lh.cad_state = cs
        _lh.graph_extractor = ge
        _lh.patch_emitter = pe
        _lh.action_executor = ae

        pe.start()

        # Register custom event for thread marshaling
        custom_event = app.registerCustomEvent("FusionMCPCommandEvent")
        custom_event_handler = CommandEventHandler()
        custom_event.add(custom_event_handler)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        ui.messageBox(f"MCP Bridge running on localhost:{PORT}")

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to start: {str(e)}\n{traceback.format_exc()}")


def stop(context):
    global server, ui, app, custom_event, custom_event_handler

    try:
        if _bh.patch_emitter:
            _bh.patch_emitter.stop()

        if server:
            server.shutdown()
            server = None

        if custom_event:
            if custom_event_handler:
                custom_event.remove(custom_event_handler)
            app.unregisterCustomEvent("FusionMCPCommandEvent")
            custom_event = None
            custom_event_handler = None

        if ui:
            ui.messageBox("MCP Bridge stopped")

    except Exception as e:
        if ui:
            ui.messageBox(f"Error stopping: {str(e)}")
