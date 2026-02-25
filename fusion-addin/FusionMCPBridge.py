"""
Fusion 360 MCP Bridge Add-in — slim orchestrator.

Delegates handlers to domain modules:
  - handlers_sketch  (complete sketch domain — 38 endpoints)
  - handlers_cam     (CAM operations)
  - handlers_model   (features, bodies, transforms, params, utility)
  - handlers_nav     (STATE / PATCH / LOCAL_GRAPH)
  - handlers_frame   (reference frame management)

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

# Sketch routes (38 endpoints)
ROUTES.update(SKETCH_ROUTES)

# Solid/body routes
ROUTES.update(SOLID_ROUTES)

# Construction / reference geometry routes
ROUTES.update(CONSTRUCTION_ROUTES)

# Camera / viewport / screenshot routes
ROUTES.update(CAMERA_ROUTES)

# Navigation / indexing (STATE, PATCH, LOCAL_GRAPH, frames, entity resolver, actions)
ROUTES.update(NAV_ROUTES)

# Timeline (22 endpoints — query, navigate, modify, group, analysis)
ROUTES.update(TIMELINE_ROUTES)

# Assembly / component / organization (20 endpoints)
ROUTES.update(ASSEMBLY_ROUTES)

# Legacy backward-compat aliases for old timeline routes
ROUTES.update({
    "/undo": TIMELINE_ROUTES["/timeline_undo"],
    "/redo": TIMELINE_ROUTES["/timeline_redo"],
    "/get_timeline": TIMELINE_ROUTES["/timeline_list"],
    "/get_feature_parameters": TIMELINE_ROUTES["/timeline_feature_params"],
    "/edit_feature_parameter": TIMELINE_ROUTES["/timeline_edit_param"],
})

# Legacy routes — document, components, params, appearance, utility, CAM.
# These remain in _legacy_handlers.py and will be incrementally extracted.
ROUTES.update({
    # Document
    "/ping": _lh.handle_ping,
    "/info": _lh.handle_info,
    "/new_document": _lh.handle_new_document,
    "/open_document": _lh.handle_open_document,
    "/save": _lh.handle_save,
    "/get_all_parts": _lh.handle_get_all_parts,

    # Parameters
    "/create_parameter": _lh.handle_create_parameter,
    "/modify_parameter": _lh.handle_modify_parameter,
    "/list_parameters": _lh.handle_list_parameters,
    "/list_all_parameters": _lh.handle_list_all_parameters,

    # Appearance
    "/apply_appearance": _lh.handle_apply_appearance,
    "/list_appearances": _lh.handle_list_appearances,

    # Utility
    "/switch_workspace": _lh.handle_switch_workspace,

    # CAM
    "/cam_list_setups": _lh.handle_cam_list_setups,
    "/cam_create_setup": _lh.handle_cam_create_setup,
    "/cam_fix_setup": _lh.handle_cam_fix_setup,
    "/cam_list_tools": _lh.handle_cam_list_tools,
    "/cam_create_2d_contour": _lh.handle_cam_create_2d_contour,
    "/cam_create_2d_pocket": _lh.handle_cam_create_2d_pocket,
    "/cam_create_engrave": _lh.handle_cam_create_engrave,
    "/cam_create_trace": _lh.handle_cam_create_trace,
    "/cam_generate_all": _lh.handle_cam_generate_all,
    "/cam_post_process": _lh.handle_cam_post_process,
    "/cam_list_operations": _lh.handle_cam_list_operations,
    "/cam_simulate": _lh.handle_cam_simulate,
    "/cam_select_silhouette": _lh.handle_cam_select_silhouette,
    "/cam_derive_body": _lh.handle_cam_derive_body,
    "/cam_create_face": _lh.handle_cam_create_face,
    "/cam_create_contour_advanced": _lh.handle_cam_create_contour_advanced,
    "/cam_create_miter_clearing": _lh.handle_cam_create_miter_clearing,
    "/cam_create_keepout": _lh.handle_cam_create_keepout,
    "/cam_set_model": _lh.handle_cam_set_model,
    "/cam_get_setup_params": _lh.handle_cam_get_setup_params,
    "/cam_set_fixture": _lh.handle_cam_set_fixture,
})


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
