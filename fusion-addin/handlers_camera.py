"""Camera, viewport, and screenshot handlers.

Controls the Fusion 360 viewport camera — preset views, free orbit,
look-at targeting, zoom, screenshots, and file export.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in CAMERA_ROUTES by the main bridge orchestrator.
"""
import base64
import math
import os
import tempfile
import traceback

import adsk.core
import adsk.fusion

try:
    from bridge_helpers import get_design, get_root
except ImportError:
    from .bridge_helpers import get_design, get_root


def _get_viewport():
    app = adsk.core.Application.get()
    vp = app.activeViewport
    if not vp:
        raise Exception("No active viewport")
    return vp


_ORIENTATIONS = {
    "top": adsk.core.ViewOrientations.TopViewOrientation,
    "bottom": adsk.core.ViewOrientations.BottomViewOrientation,
    "front": adsk.core.ViewOrientations.FrontViewOrientation,
    "back": adsk.core.ViewOrientations.BackViewOrientation,
    "left": adsk.core.ViewOrientations.LeftViewOrientation,
    "right": adsk.core.ViewOrientations.RightViewOrientation,
    "isometric": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
    "iso_top_right": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
    "iso_top_left": adsk.core.ViewOrientations.IsoTopLeftViewOrientation,
    "iso_bottom_right": adsk.core.ViewOrientations.IsoBottomRightViewOrientation,
    "iso_bottom_left": adsk.core.ViewOrientations.IsoBottomLeftViewOrientation,
}


# ── Camera state ──────────────────────────────────────────────

def handle_get_camera(body):
    """Return the current camera state — eye, target, up vector, FOV, type."""
    try:
        vp = _get_viewport()
        cam = vp.camera
        eye = cam.eye
        target = cam.target
        up = cam.upVector

        result = {
            "eye_mm": [round(eye.x * 10, 4), round(eye.y * 10, 4), round(eye.z * 10, 4)],
            "target_mm": [round(target.x * 10, 4), round(target.y * 10, 4), round(target.z * 10, 4)],
            "up_vector": [round(up.x, 6), round(up.y, 6), round(up.z, 6)],
            "is_perspective": cam.cameraType == adsk.core.CameraTypes.PerspectiveCameraType,
        }

        if cam.cameraType == adsk.core.CameraTypes.PerspectiveCameraType:
            result["perspective_angle_deg"] = round(math.degrees(cam.perspectiveAngle), 2)
        else:
            result["view_extents_mm"] = round(cam.viewExtents * 10, 4)

        dx = eye.x - target.x
        dy = eye.y - target.y
        dz = eye.z - target.z
        result["distance_mm"] = round(math.sqrt(dx*dx + dy*dy + dz*dz) * 10, 4)

        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_set_camera(body):
    """Set the camera to an exact eye/target/up position.

    Args:
        eye: [x, y, z] camera position in mm
        target: [x, y, z] look-at point in mm
        up: [x, y, z] up vector (default [0, 0, 1])
        perspective_angle: FOV in degrees (sets perspective mode)
        view_extents: Orthographic extents in mm (sets ortho mode)
        smooth: Whether to animate the transition (default True)
    """
    try:
        vp = _get_viewport()
        cam = vp.camera

        eye = body.get("eye")
        target = body.get("target")
        up = body.get("up", [0, 0, 1])
        smooth = body.get("smooth", True)

        if eye:
            cam.eye = adsk.core.Point3D.create(eye[0]/10, eye[1]/10, eye[2]/10)
        if target:
            cam.target = adsk.core.Point3D.create(target[0]/10, target[1]/10, target[2]/10)
        if up:
            cam.upVector = adsk.core.Vector3D.create(up[0], up[1], up[2])

        if body.get("perspective_angle"):
            cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
            cam.perspectiveAngle = math.radians(body["perspective_angle"])
        elif body.get("view_extents"):
            cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
            cam.viewExtents = body["view_extents"] / 10.0

        cam.isSmoothTransition = smooth
        vp.camera = cam
        adsk.doEvents()
        return {"success": True}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Preset views ──────────────────────────────────────────────

def handle_set_view(body):
    """Set the viewport to a preset orientation.

    Args:
        preset: top, bottom, front, back, left, right, isometric,
                iso_top_left, iso_bottom_right, iso_bottom_left
        fit: Whether to fit the view to all geometry (default True)
    """
    try:
        vp = _get_viewport()
        preset = body.get("preset", "isometric")
        fit = body.get("fit", True)

        cam = vp.camera
        if preset in _ORIENTATIONS:
            cam.viewOrientation = _ORIENTATIONS[preset]
        else:
            raise Exception(f"Unknown preset: {preset}. Options: {list(_ORIENTATIONS.keys())}")

        if fit:
            cam.isFitView = True

        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()
        return {"success": True, "preset": preset}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_fit_view(body):
    """Fit the view to show all geometry, optionally targeting specific entities."""
    try:
        vp = _get_viewport()
        cam = vp.camera
        cam.isFitView = True
        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()
        return {"success": True}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Camera movements ─────────────────────────────────────────

def handle_orbit(body):
    """Orbit the camera around the target point.

    Args:
        yaw: Horizontal rotation in degrees (positive = right)
        pitch: Vertical rotation in degrees (positive = up)
        smooth: Animate transition (default True)
    """
    try:
        vp = _get_viewport()
        cam = vp.camera
        eye = cam.eye
        target = cam.target
        up = cam.upVector

        yaw_deg = body.get("yaw", 0)
        pitch_deg = body.get("pitch", 0)
        yaw = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)

        dx = eye.x - target.x
        dy = eye.y - target.y
        dz = eye.z - target.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Current spherical coords
        theta = math.atan2(dy, dx)
        phi = math.acos(max(-1, min(1, dz / dist))) if dist > 1e-10 else 0

        theta += yaw
        phi = max(0.01, min(math.pi - 0.01, phi - pitch))

        new_eye = adsk.core.Point3D.create(
            target.x + dist * math.sin(phi) * math.cos(theta),
            target.y + dist * math.sin(phi) * math.sin(theta),
            target.z + dist * math.cos(phi),
        )

        cam.eye = new_eye
        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()

        return {"success": True, "yaw": yaw_deg, "pitch": pitch_deg,
                "eye_mm": [round(new_eye.x*10, 2), round(new_eye.y*10, 2), round(new_eye.z*10, 2)]}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_zoom(body):
    """Zoom in or out by a factor.

    Args:
        factor: Zoom multiplier (>1 = zoom in, <1 = zoom out). Default 1.5
        smooth: Animate (default True)
    """
    try:
        vp = _get_viewport()
        cam = vp.camera
        factor = body.get("factor", 1.5)

        if cam.cameraType == adsk.core.CameraTypes.PerspectiveCameraType:
            eye = cam.eye
            target = cam.target
            dx = eye.x - target.x
            dy = eye.y - target.y
            dz = eye.z - target.z
            cam.eye = adsk.core.Point3D.create(
                target.x + dx / factor,
                target.y + dy / factor,
                target.z + dz / factor,
            )
        else:
            cam.viewExtents = cam.viewExtents / factor

        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()
        return {"success": True, "factor": factor}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_pan(body):
    """Pan the camera (move eye and target together).

    Args:
        offset: [x, y, z] offset in mm (in world coordinates)
        smooth: Animate (default True)
    """
    try:
        vp = _get_viewport()
        cam = vp.camera
        offset = body.get("offset", [0, 0, 0])
        ox, oy, oz = offset[0]/10, offset[1]/10, offset[2]/10

        eye = cam.eye
        target = cam.target
        cam.eye = adsk.core.Point3D.create(eye.x + ox, eye.y + oy, eye.z + oz)
        cam.target = adsk.core.Point3D.create(target.x + ox, target.y + oy, target.z + oz)

        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()
        return {"success": True, "offset_mm": offset}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_look_at(body):
    """Point the camera at a specific target while keeping the current distance.

    Args:
        target: [x, y, z] point to look at in mm
        distance: Optional distance from target in mm (default: keep current)
        elevation: Optional elevation angle in degrees (default: keep current)
        azimuth: Optional azimuth angle in degrees (default: keep current)
        smooth: Animate (default True)
    """
    try:
        vp = _get_viewport()
        cam = vp.camera

        new_target = body.get("target")
        if not new_target:
            raise Exception("target [x, y, z] is required")

        old_eye = cam.eye
        old_target = cam.target
        dx = old_eye.x - old_target.x
        dy = old_eye.y - old_target.y
        dz = old_eye.z - old_target.z
        current_dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        dist_cm = body.get("distance", current_dist * 10) / 10.0

        tx, ty, tz = new_target[0]/10, new_target[1]/10, new_target[2]/10

        if body.get("elevation") is not None or body.get("azimuth") is not None:
            elev = math.radians(body.get("elevation", 30))
            azim = math.radians(body.get("azimuth", 45))
            ex = tx + dist_cm * math.cos(elev) * math.cos(azim)
            ey = ty + dist_cm * math.cos(elev) * math.sin(azim)
            ez = tz + dist_cm * math.sin(elev)
        else:
            if current_dist > 1e-10:
                scale = dist_cm / current_dist
            else:
                scale = 1
            ex = tx + dx * scale
            ey = ty + dy * scale
            ez = tz + dz * scale

        cam.target = adsk.core.Point3D.create(tx, ty, tz)
        cam.eye = adsk.core.Point3D.create(ex, ey, ez)
        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()

        return {"success": True,
                "target_mm": new_target,
                "eye_mm": [round(ex*10, 2), round(ey*10, 2), round(ez*10, 2)]}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_set_projection(body):
    """Switch between perspective and orthographic projection.

    Args:
        type: "perspective" or "orthographic"
        perspective_angle: FOV in degrees (for perspective, default 60)
    """
    try:
        vp = _get_viewport()
        old_cam = vp.camera
        proj = body.get("type", "perspective")

        if proj == "perspective":
            eye = old_cam.eye
            target = old_cam.target
            up = old_cam.upVector
            cam = adsk.core.Camera.create()
            cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
            cam.eye = eye
            cam.target = target
            cam.upVector = up
            fov = body.get("perspective_angle", 60)
            cam.perspectiveAngle = math.radians(fov)
        elif proj == "orthographic":
            cam = old_cam
            cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        else:
            raise Exception(f"Unknown projection type: {proj}")

        cam.isSmoothTransition = body.get("smooth", True)
        vp.camera = cam
        adsk.doEvents()
        return {"success": True, "projection": proj}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Visual style ──────────────────────────────────────────────

def handle_set_visual_style(body):
    """Set the viewport visual style.

    Args:
        style: shaded, wireframe, shaded_wireframe, hidden_edges
    """
    try:
        vp = _get_viewport()
        style = body.get("style", "shaded")

        style_map = {
            "shaded": adsk.core.VisualStyles.ShadedVisualStyle,
            "wireframe": adsk.core.VisualStyles.WireframeVisualStyle,
            "shaded_wireframe": adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle,
            "hidden_edges": adsk.core.VisualStyles.ShadedWithHiddenEdgesVisualStyle,
        }

        if style not in style_map:
            raise Exception(f"Unknown style: {style}. Options: {list(style_map.keys())}")

        vp.visualStyle = style_map[style]
        adsk.doEvents()
        return {"success": True, "style": style}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Screenshot ────────────────────────────────────────────────

def handle_take_screenshot(body):
    """Capture the current viewport as a PNG image.

    Args:
        width: Image width in pixels (default 1920)
        height: Image height in pixels (default 1080)
        view: Optional preset view to set first (top, front, isometric, etc.)
        path: Optional file path to save to (returns base64 if omitted)
    """
    try:
        vp = _get_viewport()
        width = body.get("width", 1920)
        height = body.get("height", 1080)
        view_preset = body.get("view")
        save_path = body.get("path")

        if view_preset and view_preset != "current":
            cam = vp.camera
            if view_preset in _ORIENTATIONS:
                cam.viewOrientation = _ORIENTATIONS[view_preset]
                cam.isFitView = True
                vp.camera = cam
                adsk.doEvents()

        if save_path:
            out_path = os.path.expanduser(save_path)
        else:
            out_path = os.path.join(tempfile.gettempdir(), "fusion_screenshot.png")

        success = vp.saveAsImageFile(out_path, width, height)
        if not success or not os.path.exists(out_path):
            return {"error": True, "message": "Failed to save screenshot"}

        result = {"success": True, "width": width, "height": height, "format": "png"}

        if save_path:
            result["path"] = out_path
            result["file_size"] = os.path.getsize(out_path)
        else:
            with open(out_path, "rb") as f:
                result["image_base64"] = base64.b64encode(f.read()).decode()
            try:
                os.remove(out_path)
            except Exception:
                pass

        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_screenshot_to_file(body):
    """Save a screenshot directly to a file path.

    Args:
        path: File path to save the PNG (required)
        width: Pixel width (default 1920)
        height: Pixel height (default 1080)
        view: Optional preset view
    """
    path = body.get("path")
    if not path:
        raise Exception("path is required")
    body["path"] = path
    return handle_take_screenshot(body)


# ── Export ────────────────────────────────────────────────────

def handle_export(body):
    """Export the design to a file.

    Args:
        format: stl, step, iges, f3d (default: stl)
        path: Output file path (required)
        options: {refinement: low|medium|high} for STL
    """
    try:
        design = get_design()
        export_mgr = design.exportManager
        fmt = body.get("format", "stl")
        path = body.get("path")

        if not path:
            raise Exception("Export path is required")
        path = os.path.expanduser(path)

        if fmt == "stl":
            options = export_mgr.createSTLExportOptions(design.rootComponent)
            options.filename = path
            refinement = body.get("options", {}).get("refinement", "medium")
            ref_map = {
                "low": adsk.fusion.MeshRefinementSettings.MeshRefinementLow,
                "medium": adsk.fusion.MeshRefinementSettings.MeshRefinementMedium,
                "high": adsk.fusion.MeshRefinementSettings.MeshRefinementHigh,
            }
            options.meshRefinement = ref_map.get(refinement, ref_map["medium"])
        elif fmt == "step":
            options = export_mgr.createSTEPExportOptions(path)
        elif fmt == "iges":
            options = export_mgr.createIGESExportOptions(path)
        elif fmt == "f3d":
            options = export_mgr.createFusionArchiveExportOptions(path)
        else:
            raise Exception(f"Unsupported format: {fmt}. Use: stl, step, iges, f3d")

        export_mgr.execute(options)
        file_size = os.path.getsize(path) if os.path.exists(path) else 0

        return {"success": True, "path": path, "format": fmt, "file_size": file_size}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Route table ───────────────────────────────────────────────

CAMERA_ROUTES = {
    # Camera state
    "/get_camera": handle_get_camera,
    "/set_camera": handle_set_camera,

    # Preset views
    "/set_view": handle_set_view,
    "/fit_view": handle_fit_view,

    # Camera movements
    "/orbit": handle_orbit,
    "/zoom": handle_zoom,
    "/pan": handle_pan,
    "/look_at": handle_look_at,

    # Projection & style
    "/set_projection": handle_set_projection,
    "/set_visual_style": handle_set_visual_style,

    # Screenshot
    "/take_screenshot": handle_take_screenshot,
    "/screenshot_to_file": handle_screenshot_to_file,

    # Export
    "/export": handle_export,
}
