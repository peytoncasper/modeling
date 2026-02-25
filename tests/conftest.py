"""Shared fixtures and adsk mock setup for testing Fusion bridge handlers.

The adsk module is only available inside Fusion 360's embedded Python.
We inject a mock module tree so handler code can be imported and exercised
outside of Fusion.
"""

import sys
import math
import types
from unittest.mock import MagicMock, PropertyMock
import pytest


# ── Mock adsk module tree ─────────────────────────────────────

def _build_adsk_mocks():
    """Build a realistic mock of the adsk module hierarchy."""
    adsk = types.ModuleType("adsk")
    adsk.core = types.ModuleType("adsk.core")
    adsk.fusion = types.ModuleType("adsk.fusion")
    adsk.cam = types.ModuleType("adsk.cam")

    # Point3D — stores real coordinates so geometry math works
    class FakePoint3D:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x = x
            self.y = y
            self.z = z

        @staticmethod
        def create(x, y, z):
            return FakePoint3D(x, y, z)

        def transformBy(self, transform):
            pass

        def copy(self):
            return FakePoint3D(self.x, self.y, self.z)

        def __repr__(self):
            return f"FakePoint3D({self.x}, {self.y}, {self.z})"

    class FakeVector3D:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.x = x
            self.y = y
            self.z = z

        @staticmethod
        def create(x, y, z):
            return FakeVector3D(x, y, z)

    class FakeObjectCollection:
        def __init__(self):
            self._items = []
            self.count = 0

        def add(self, item):
            self._items.append(item)
            self.count = len(self._items)

        def item(self, i):
            return self._items[i]

        @staticmethod
        def create():
            return FakeObjectCollection()

    class FakeValueInput:
        def __init__(self, val):
            self.realValue = val

        @staticmethod
        def createByReal(val):
            return FakeValueInput(val)

    adsk.core.Point3D = FakePoint3D
    adsk.core.Vector3D = FakeVector3D
    adsk.core.ObjectCollection = FakeObjectCollection
    adsk.core.ValueInput = FakeValueInput
    adsk.core.Application = MagicMock()
    adsk.core.CustomEventHandler = type("CustomEventHandler", (), {})
    adsk.core.SurfaceTypes = MagicMock()
    adsk.core.SurfaceTypes.PlaneSurfaceType = 0

    adsk.fusion.Design = MagicMock()
    adsk.fusion.DimensionOrientations = MagicMock()
    adsk.fusion.DimensionOrientations.AlignedDimensionOrientation = 0

    adsk.doEvents = MagicMock()

    return adsk


@pytest.fixture(autouse=True)
def adsk_mocks():
    """Inject adsk mocks into sys.modules before any handler import."""
    adsk = _build_adsk_mocks()
    originals = {}
    for mod_name in ["adsk", "adsk.core", "adsk.fusion", "adsk.cam"]:
        originals[mod_name] = sys.modules.get(mod_name)

    sys.modules["adsk"] = adsk
    sys.modules["adsk.core"] = adsk.core
    sys.modules["adsk.fusion"] = adsk.fusion
    sys.modules["adsk.cam"] = adsk.cam

    yield adsk

    for mod_name, orig in originals.items():
        if orig is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = orig


# ── Fake Fusion sketch objects ────────────────────────────────

class FakeSketchPoint:
    def __init__(self, x=0.0, y=0.0):
        self.geometry = sys.modules["adsk"].core.Point3D.create(x, y, 0)
        self.connectedEntities = MagicMock(count=0)

    def move(self, vector):
        self.geometry.x += vector.x
        self.geometry.y += vector.y


class FakeLine:
    objectType = "adsk::fusion::SketchLine"

    def __init__(self, sx, sy, ex, ey, construction=False):
        self.startSketchPoint = FakeSketchPoint(sx, sy)
        self.endSketchPoint = FakeSketchPoint(ex, ey)
        self.isConstruction = construction
        self.length = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
        self.isClosed = False


class FakeCircle:
    objectType = "adsk::fusion::SketchCircle"

    def __init__(self, cx, cy, r):
        self.centerSketchPoint = FakeSketchPoint(cx, cy)
        self.radius = r
        self.isClosed = True


class FakeArc:
    objectType = "adsk::fusion::SketchArc"

    def __init__(self, cx, cy, sx, sy, ex, ey):
        self.centerSketchPoint = FakeSketchPoint(cx, cy)
        self.startSketchPoint = FakeSketchPoint(sx, sy)
        self.endSketchPoint = FakeSketchPoint(ex, ey)
        self.isClosed = False


class FakeCurveCollection:
    """Mimics sketch.sketchCurves with typed sub-collections."""

    def __init__(self):
        self._items = []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def __iter__(self):
        return iter(self._items)

    def _make_line_sub(self):
        parent = self

        class Lines:
            def addByTwoPoints(self, start_pt, end_pt):
                line = FakeLine(start_pt.x, start_pt.y, end_pt.x, end_pt.y)
                parent._items.append(line)
                return line

            def addTwoPointRectangle(self, c1, c2):
                lines = [
                    FakeLine(c1.x, c1.y, c2.x, c1.y),
                    FakeLine(c2.x, c1.y, c2.x, c2.y),
                    FakeLine(c2.x, c2.y, c1.x, c2.y),
                    FakeLine(c1.x, c2.y, c1.x, c1.y),
                ]
                parent._items.extend(lines)
                return lines

            def item(self, i):
                idx = 0
                for c in parent._items:
                    if isinstance(c, FakeLine):
                        if idx == i:
                            return c
                        idx += 1
                raise IndexError(i)

        return Lines()

    def _make_circle_sub(self):
        parent = self

        class Circles:
            def addByCenterRadius(self, center, radius):
                c = FakeCircle(center.x, center.y, radius)
                parent._items.append(c)
                return c

        return Circles()

    def _make_arc_sub(self):
        parent = self

        class Arcs:
            def addByCenterStartSweep(self, center, start_pt, sweep):
                a = FakeArc(center.x, center.y, start_pt.x, start_pt.y,
                            start_pt.x, start_pt.y)
                parent._items.append(a)
                return a

            def addByThreePoints(self, start, mid, end):
                a = FakeArc(0, 0, start.x, start.y, end.x, end.y)
                parent._items.append(a)
                return a

            def addFillet(self, c1, p1, c2, p2, radius):
                a = FakeArc(0, 0, p1.x, p1.y, p2.x, p2.y)
                parent._items.append(a)
                return a

        return Arcs()

    def _make_spline_sub(self):
        parent = self

        class Splines:
            def add(self, points_collection):
                first = points_collection.item(0)
                last = points_collection.item(points_collection.count - 1)
                line = FakeLine(first.x, first.y, last.x, last.y)
                line.isClosed = False
                parent._items.append(line)
                return line

        return Splines()

    @property
    def sketchLines(self):
        return self._make_line_sub()

    @property
    def sketchCircles(self):
        return self._make_circle_sub()

    @property
    def sketchArcs(self):
        return self._make_arc_sub()

    @property
    def sketchFittedSplines(self):
        return self._make_spline_sub()


class FakePointCollection:
    def __init__(self):
        self._items = []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def add(self, pt):
        sp = FakeSketchPoint(pt.x, pt.y)
        self._items.append(sp)
        return sp


class FakeProfile:
    def __init__(self, area=100.0, min_pt=None, max_pt=None):
        self._area = area
        Pt = sys.modules["adsk"].core.Point3D
        min_pt = min_pt or Pt.create(0, 0, 0)
        max_pt = max_pt or Pt.create(1, 1, 0)
        self.boundingBox = MagicMock()
        self.boundingBox.minPoint = min_pt
        self.boundingBox.maxPoint = max_pt

    def areaProperties(self):
        m = MagicMock()
        m.area = self._area
        return m


class FakeProfileCollection:
    def __init__(self, profiles=None):
        self._items = profiles or []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]


class FakeDimension:
    def __init__(self, value_cm=1.0, expression="10 mm"):
        self.value = value_cm
        self.parameter = MagicMock()
        self.parameter.expression = expression
        self.parameter.name = "d0"
        self.objectType = "adsk::fusion::SketchLinearDimension"
        self.textPosition = sys.modules["adsk"].core.Point3D.create(0, 0, 0)


class FakeDimensionCollection:
    def __init__(self, dims=None):
        self._items = dims or []

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        return self._items[i]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def addDistanceDimension(self, *args, **kwargs):
        d = FakeDimension()
        self._items.append(d)
        return d

    def addDiameterDimension(self, *args, **kwargs):
        d = FakeDimension()
        self._items.append(d)
        return d

    def addRadialDimension(self, *args, **kwargs):
        d = FakeDimension()
        self._items.append(d)
        return d

    def addAngularDimension(self, *args, **kwargs):
        d = FakeDimension()
        self._items.append(d)
        return d


class FakeGeometricConstraints:
    def __init__(self):
        self._items = []
        self.count = 0

    def item(self, i):
        return self._items[i]

    def _add(self, ctype):
        m = MagicMock(objectType=f"adsk::fusion::{ctype}")
        self._items.append(m)
        self.count = len(self._items)
        return m

    def addCoincident(self, *a): return self._add("CoincidentConstraint")
    def addHorizontal(self, *a): return self._add("HorizontalConstraint")
    def addVertical(self, *a): return self._add("VerticalConstraint")
    def addPerpendicular(self, *a): return self._add("PerpendicularConstraint")
    def addParallel(self, *a): return self._add("ParallelConstraint")
    def addTangent(self, *a): return self._add("TangentConstraint")
    def addEqual(self, *a): return self._add("EqualConstraint")
    def addConcentric(self, *a): return self._add("ConcentricConstraint")
    def addMidPoint(self, *a): return self._add("MidPointConstraint")
    def addFix(self, *a): return self._add("FixConstraint")
    def addCollinear(self, *a): return self._add("CollinearConstraint")


class FakeSketchTexts:
    def createInput(self, text, height, position):
        inp = MagicMock()
        inp.fontName = "Arial"
        inp.angle = 0
        inp.isBold = False
        inp.isItalic = False
        return inp

    def add(self, text_input):
        return MagicMock()


class FakeNormal:
    def __init__(self, x=0, y=0, z=1):
        self.x = x
        self.y = y
        self.z = z


class FakeGeometry:
    def __init__(self, normal=None, origin=None):
        Pt = sys.modules["adsk"].core.Point3D
        self.normal = normal or FakeNormal()
        self.origin = origin or Pt.create(0, 0, 0)


class FakePlane:
    def __init__(self, plane_type="XY"):
        normals = {"XY": (0, 0, 1), "XZ": (0, 1, 0), "YZ": (1, 0, 0)}
        nx, ny, nz = normals.get(plane_type, (0, 0, 1))
        self.geometry = FakeGeometry(FakeNormal(nx, ny, nz))

    @property
    def name(self):
        return "ConstructionPlane"


class FakeSketch:
    """Minimal fake of adsk.fusion.Sketch."""

    def __init__(self, name="TestSketch", plane_type="XY"):
        self.name = name
        self.sketchCurves = FakeCurveCollection()
        self.sketchPoints = FakePointCollection()
        self.profiles = FakeProfileCollection([FakeProfile()])
        self.sketchDimensions = FakeDimensionCollection()
        self.geometricConstraints = FakeGeometricConstraints()
        self.sketchTexts = FakeSketchTexts()
        self.referencePlane = FakePlane(plane_type)
        self.isFullyConstrained = False
        Pt = sys.modules["adsk"].core.Point3D
        self.transform = MagicMock()
        self.transform.transformBy = MagicMock()

    def trim(self, curve, point):
        pass

    def extend(self, curve, point, endpoint):
        pass

    def offset(self, curves, direction, distance):
        pass

    def mirror(self, curves, line):
        pass

    def importSVG(self, path, x, y, scale):
        pass

    def deleteMe(self):
        pass


class FakeSketchCollection:
    def __init__(self, sketches=None):
        self._items = {s.name: s for s in (sketches or [])}

    def add(self, plane):
        s = FakeSketch("NewSketch")
        self._items[s.name] = s
        return s

    def itemByName(self, name):
        return self._items.get(name)

    def __iter__(self):
        return iter(self._items.values())


class FakeConstructionPlanes:
    def itemByName(self, name):
        return None


class FakeBody:
    def __init__(self, name="Body1"):
        self.name = name
        self.faces = MagicMock(count=1)
        self.faces.item = MagicMock(return_value=MagicMock())
        self.boundingBox = MagicMock()
        Pt = sys.modules["adsk"].core.Point3D
        self.boundingBox.minPoint = Pt.create(0, 0, 0)
        self.boundingBox.maxPoint = Pt.create(1, 1, 1)


class FakeBodyCollection:
    def __init__(self, bodies=None):
        self._items = bodies or []

    def __iter__(self):
        return iter(self._items)


class FakeOccurrence:
    def __init__(self, comp):
        self.component = comp
        self.name = comp.name


class FakeComponent:
    def __init__(self, name="root", sketches=None, bodies=None):
        self.name = name
        self.sketches = FakeSketchCollection(sketches or [])
        self.bRepBodies = FakeBodyCollection(bodies or [])
        self.xYConstructionPlane = FakePlane("XY")
        self.xZConstructionPlane = FakePlane("XZ")
        self.yZConstructionPlane = FakePlane("YZ")
        self.constructionPlanes = FakeConstructionPlanes()
        self.allOccurrences = []


@pytest.fixture
def fake_sketch():
    """Create a pre-populated FakeSketch."""
    s = FakeSketch("S1")
    return s


@pytest.fixture
def fake_component(fake_sketch):
    """Create a FakeComponent with one sketch."""
    comp = FakeComponent(name="root", sketches=[fake_sketch])
    return comp


@pytest.fixture
def patch_helpers(adsk_mocks, fake_component, monkeypatch):
    """Patch bridge_helpers so handler imports see our fakes."""
    sys.path.insert(0, "/Users/peytocas/Documents/modeling/fusion-addin")
    import bridge_helpers as bh
    monkeypatch.setattr(bh, "app", MagicMock())
    monkeypatch.setattr(bh, "get_root", lambda: fake_component)
    monkeypatch.setattr(bh, "get_design", lambda: MagicMock(rootComponent=fake_component))

    original_get_sketch = bh.get_sketch

    def patched_get_sketch(sketch_id):
        s = fake_component.sketches.itemByName(sketch_id)
        if s:
            return s
        raise Exception(f"Sketch not found: {sketch_id}")

    monkeypatch.setattr(bh, "get_sketch", patched_get_sketch)
    yield bh
    sys.path.remove("/Users/peytocas/Documents/modeling/fusion-addin")
