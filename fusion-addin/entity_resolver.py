"""Stable entity reference system for Fusion 360.

Provides dual-reference (id + semantic key) that survives timeline edits.
When a native entityToken goes stale, the semantic key re-resolves by
walking parent features and scoring candidates on geometric heuristics.
"""

import math
from typing import Dict, List, Optional, Any, Tuple


class SemanticKey:
    """Deterministic fallback locator for a Fusion entity."""

    __slots__ = ("type", "of", "where")

    def __init__(self, type: str, of: Optional[Dict[str, str]] = None,
                 where: Optional[Dict[str, Any]] = None):
        self.type = type
        self.of = of or {}
        self.where = where or {}

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.of:
            d["of"] = self.of
        if self.where:
            d["where"] = self.where
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticKey":
        return cls(
            type=data["type"],
            of=data.get("of", {}),
            where=data.get("where", {}),
        )

    def __repr__(self):
        return f"SemanticKey({self.type}, of={self.of}, where={self.where})"


class EntityRef:
    """Dual reference: fast native id + stable semantic key."""

    __slots__ = ("id", "key", "_stale")

    def __init__(self, id: str, key: Optional[SemanticKey] = None):
        self.id = id
        self.key = key
        self._stale = False

    def to_dict(self) -> dict:
        d = {"id": self.id}
        if self.key:
            d["key"] = self.key.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EntityRef":
        key = SemanticKey.from_dict(data["key"]) if "key" in data else None
        return cls(id=data["id"], key=key)

    def mark_stale(self):
        self._stale = True

    @property
    def is_stale(self) -> bool:
        return self._stale

    def __repr__(self):
        stale = " STALE" if self._stale else ""
        return f"EntityRef({self.id}{stale}, key={self.key})"


def _vec_len(v: List[float]) -> float:
    return math.sqrt(sum(c * c for c in v))


def _vec_dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _normal_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two normal vectors. Returns 0..1."""
    la, lb = _vec_len(a), _vec_len(b)
    if la < 1e-9 or lb < 1e-9:
        return 0.0
    return max(0.0, _vec_dot(a, b) / (la * lb))


def _point_distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class EntityResolver:
    """Resolves EntityRefs to live Fusion entities.

    Keeps a cache of id -> EntityRef so that when a native token goes stale
    the semantic key can re-resolve it.
    """

    def __init__(self):
        self._cache: Dict[str, EntityRef] = {}

    def register(self, ref: EntityRef):
        self._cache[ref.id] = ref

    def get_ref(self, id: str) -> Optional[EntityRef]:
        return self._cache.get(id)

    def clear(self):
        self._cache.clear()

    # ------------------------------------------------------------------
    # Key generation helpers (called once when entity first encountered)
    # ------------------------------------------------------------------

    def make_body_ref(self, body) -> EntityRef:
        """Create an EntityRef for a BRepBody."""
        token = body.entityToken
        key = SemanticKey(
            type="body",
            of={"name": body.name},
            where={
                "volume_mm3": round(body.volume * 1000, 2),
                "face_count": body.faces.count,
            },
        )
        ref = EntityRef(id=token, key=key)
        self.register(ref)
        return ref

    def make_face_ref(self, face, body_name: str, face_index: int) -> EntityRef:
        """Create an EntityRef for a BRepFace."""
        token = face.entityToken
        geo = face.geometry

        normal = None
        if hasattr(geo, "normal"):
            n = geo.normal
            normal = [round(n.x, 4), round(n.y, 4), round(n.z, 4)]

        centroid = face.centroid
        centroid_mm = [
            round(centroid.x * 10, 2),
            round(centroid.y * 10, 2),
            round(centroid.z * 10, 2),
        ]

        key = SemanticKey(
            type="face",
            of={"body": body_name, "index": face_index},
            where={
                "normal": normal,
                "centroid_mm": centroid_mm,
                "area_mm2": round(face.area * 100, 2),
            },
        )
        ref = EntityRef(id=token, key=key)
        self.register(ref)
        return ref

    def make_edge_ref(self, edge, body_name: str, edge_index: int) -> EntityRef:
        """Create an EntityRef for a BRepEdge."""
        token = edge.entityToken
        midpoint = edge.pointOnEdge
        mid_mm = [
            round(midpoint.x * 10, 2),
            round(midpoint.y * 10, 2),
            round(midpoint.z * 10, 2),
        ]

        key = SemanticKey(
            type="edge",
            of={"body": body_name, "index": edge_index},
            where={
                "midpoint_mm": mid_mm,
                "length_mm": round(edge.length * 10, 2),
            },
        )
        ref = EntityRef(id=token, key=key)
        self.register(ref)
        return ref

    def make_sketch_ref(self, sketch) -> EntityRef:
        """Create an EntityRef for a Sketch."""
        token = sketch.entityToken if hasattr(sketch, "entityToken") else sketch.name
        key = SemanticKey(
            type="sketch",
            of={"name": sketch.name},
            where={"profile_count": sketch.profiles.count},
        )
        ref = EntityRef(id=token, key=key)
        self.register(ref)
        return ref

    def make_feature_ref(self, timeline_item, index: int) -> EntityRef:
        """Create an EntityRef for a timeline feature."""
        name = "unknown"
        entity_type = "unknown"
        try:
            name = timeline_item.name
        except Exception:
            name = f"Item_{index}"
        try:
            entity_type = timeline_item.entity.objectType.split("::")[-1]
        except Exception:
            pass

        key = SemanticKey(
            type="feature",
            of={"name": name, "timeline_index": index},
            where={"feature_type": entity_type},
        )
        ref = EntityRef(id=f"feature_{name}_{index}", key=key)
        self.register(ref)
        return ref

    # ------------------------------------------------------------------
    # Resolution: ref -> live Fusion entity
    # ------------------------------------------------------------------

    def resolve_body(self, ref: EntityRef, root_component) -> Optional[Any]:
        """Resolve a body ref to a live BRepBody."""
        # Fast path: try entityToken
        for body in root_component.bRepBodies:
            if body.entityToken == ref.id:
                return body

        # Fallback: semantic key
        if not ref.key or ref.key.type != "body":
            return None

        ref.mark_stale()
        target_name = ref.key.of.get("name")
        for body in root_component.bRepBodies:
            if body.name == target_name:
                ref.id = body.entityToken
                ref._stale = False
                return body

        return None

    def resolve_face(self, ref: EntityRef, root_component) -> Optional[Any]:
        """Resolve a face ref to a live BRepFace."""
        if not ref.key or ref.key.type != "face":
            return None

        body_name = ref.key.of.get("body")
        target_body = None
        for b in root_component.bRepBodies:
            if b.name == body_name:
                target_body = b
                break
        if not target_body:
            return None

        # Fast path: try entityToken
        for face in target_body.faces:
            if face.entityToken == ref.id:
                return face

        # Fallback: score by normal + centroid + area
        ref.mark_stale()
        best, best_score = None, -1.0
        target_normal = ref.key.where.get("normal")
        target_centroid = ref.key.where.get("centroid_mm")
        target_area = ref.key.where.get("area_mm2", 0)

        for face in target_body.faces:
            score = 0.0
            geo = face.geometry

            if target_normal and hasattr(geo, "normal"):
                n = [geo.normal.x, geo.normal.y, geo.normal.z]
                score += _normal_similarity(target_normal, n) * 40

            if target_centroid:
                c = face.centroid
                c_mm = [c.x * 10, c.y * 10, c.z * 10]
                dist = _point_distance(target_centroid, c_mm)
                score += max(0, 30 - dist)

            if target_area > 0:
                area_mm2 = face.area * 100
                ratio = min(area_mm2, target_area) / max(area_mm2, target_area) if target_area > 0 else 0
                score += ratio * 30

            if score > best_score:
                best_score = score
                best = face

        if best and best_score > 50:
            ref.id = best.entityToken
            ref._stale = False
            return best
        return None

    def resolve_edge(self, ref: EntityRef, root_component) -> Optional[Any]:
        """Resolve an edge ref to a live BRepEdge.

        Fast path: entityToken match.
        Fallback: geometric scoring on midpoint distance (50),
        length ratio (30), and adjacent face normal agreement (20).
        """
        if not ref.key or ref.key.type != "edge":
            return None

        body_name = ref.key.of.get("body")
        target_body = None
        for b in root_component.bRepBodies:
            if b.name == body_name:
                target_body = b
                break
        if not target_body:
            return None

        # Fast path: entityToken
        for edge in target_body.edges:
            if edge.entityToken == ref.id:
                return edge

        # Fallback: geometric scoring
        ref.mark_stale()
        best, best_score = None, -1.0
        target_midpoint = ref.key.where.get("midpoint_mm")
        target_length = ref.key.where.get("length_mm", 0)

        for edge in target_body.edges:
            score = 0.0

            if target_midpoint:
                mp = edge.pointOnEdge
                mp_mm = [mp.x * 10, mp.y * 10, mp.z * 10]
                dist = _point_distance(target_midpoint, mp_mm)
                score += max(0, 50 - dist * 2)

            if target_length > 0:
                edge_len = edge.length * 10
                ratio = (min(edge_len, target_length)
                         / max(edge_len, target_length))
                score += ratio * 30

            try:
                faces = [edge.faces.item(i) for i in range(edge.faces.count)]
                if faces:
                    score += 10
                    for face in faces[:2]:
                        geo = face.geometry
                        if hasattr(geo, "normal"):
                            score += 5
            except Exception:
                pass

            if score > best_score:
                best_score = score
                best = edge

        if best and best_score > 50:
            ref.id = best.entityToken
            ref._stale = False
            return best
        return None

    def resolve_sketch(self, ref: EntityRef, root_component) -> Optional[Any]:
        """Resolve a sketch ref to a live Sketch."""
        target_name = ref.key.of.get("name") if ref.key else None
        if not target_name:
            target_name = ref.id

        for sketch in root_component.sketches:
            if sketch.name == target_name:
                return sketch
        return None

    def to_dict(self) -> dict:
        return {
            "refs": {k: v.to_dict() for k, v in self._cache.items()},
        }

    def load_from_dict(self, data: dict):
        self._cache.clear()
        for k, v in data.get("refs", {}).items():
            self._cache[k] = EntityRef.from_dict(v)
