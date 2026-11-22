import unittest
from dataclasses import replace
from unittest.mock import patch

from build123d import GeomType, Plane, Pos, Rot, section
from fastapi import FastAPI
from fastapi.testclient import TestClient

from argus.models.base.parameters import BASE_PARAMETERS
from argus.models.base.preview import FIELDS as BASE_FIELDS
from argus.models.base.preview import build_preview as build_base_preview
from argus.models.head.parameters import HEAD_PARAMETERS
from argus.models.head.preview import FIELDS as HEAD_FIELDS
from argus.models.head.preview import build_preview as build_head_preview
from argus.models.preview import resolve_fields
from argus.web.api import _MODELS, router


class TestWebPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    def preview(self, model, parameters):
        return self.client.post(f"/api/models/{model}/preview", json={"parameters": parameters})

    def test_default_previews_are_indexed_meshes(self):
        catalog = self.client.get("/api/models").json()["models"]
        self.assertEqual([model["id"] for model in catalog], [
            "base-split", "gimbal-assembly", "base-servo", "servo-horn-long", "servo-horn", "servo-horn-single", "sg90s",
            "base", "bracket", "bracket-print", "head", "head-print",
        ])
        for model in catalog:
            with self.subTest(model=model["id"]):
                response = self.preview(model["id"], {})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["model"], model["id"])
                self.assertEqual(
                    payload["parameters"], {field["key"]: field["default"] for field in model["fields"]},
                )
                if model["id"] in ("base-split", "gimbal-assembly"):
                    self.assertEqual(len({part["id"] for part in payload["parts"]}), 8)
                    meshes = [part["mesh"] for part in payload["parts"]]
                else:
                    meshes = [payload["mesh"]]
                for mesh in meshes:
                    vertices, indices = mesh["positions"], mesh["indices"]
                    self.assertGreater(len(vertices), 0)
                    self.assertGreater(len(indices), 0)
                    self.assertEqual(len(vertices) % 3, 0)
                    self.assertEqual(len(indices) % 3, 0)
                    self.assertGreaterEqual(min(indices), 0)
                    self.assertLess(max(indices), len(vertices) // 3)

    def test_split_base_rejects_incorrect_screw_engagement(self):
        response = self.preview("base-split", {"connection": 1, "bolt_length": 5})
        self.assertEqual(response.status_code, 422)
        self.assertIn("bolt_length", response.json()["detail"]["fields"])
        response = self.preview("base-split", {"bolt_length": 5, "snap_clearance": 0.3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parameters"]["snap_clearance"], 0.3)

    def test_field_and_geometry_errors(self):
        self.assertEqual(self.preview("missing", {}).status_code, 404)
        for data, field in [
            ({"plate_side": True}, "plate_side"),
            ({"size": 38}, "size"),
            ({"plate_side": 34, "corner_hole_pitch": 32}, "corner_hole_pitch"),
        ]:
            response = self.preview("base", data)
            self.assertEqual(response.status_code, 422)
            self.assertIn(field, response.json()["detail"]["fields"])

        def failed_build(_):
            raise RuntimeError("simulated CAD failure")

        model = replace(_MODELS["base"], build=failed_build)
        with patch.dict(_MODELS, {"base": model}), self.assertLogs("argus.web.api", level="ERROR"):
            response = self.preview("base", {})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("simulated CAD failure", response.text)

    def test_base_remains_symmetric_after_changing_its_pitch(self):
        parameters = {"plate_side": 42, "corner_hole_pitch": 34}
        response = self.preview("base", parameters)
        self.assertEqual(response.status_code, 200)
        bounds = response.json()["bounds"]
        self.assertAlmostEqual(bounds["max"][0] - bounds["min"][0], 42)
        part = build_base_preview(resolve_fields(BASE_FIELDS, parameters))
        profile = section(part, section_by=Plane((0, 0, 1.75)))
        self.assertEqual(len(profile.faces()[0].inner_wires()), 8)
        x, y = BASE_PARAMETERS.ring.center
        rotated = Pos(x, y, 0) * Rot(0, 0, 90) * Pos(-x, -y, 0) * profile
        self.assertLess(sum(face.area for face in profile.cut(rotated).faces()), 1e-6)

    def test_servo_base_regenerates_and_rejects_insufficient_floor_thickness(self):
        response = self.preview("base-servo", {"plate_side": 46, "clearance": 0.3})
        self.assertEqual(response.status_code, 200)
        bounds = response.json()["bounds"]
        self.assertAlmostEqual(bounds["max"][0] - bounds["min"][0], 46)
        response = self.preview("base-servo", {"plate_thickness": 5.2})
        self.assertEqual(response.status_code, 422)
        self.assertIn("plate_thickness", response.json()["detail"]["fields"])

    def test_selecting_a_horn_changes_the_base_pocket_and_uses_matching_defaults(self):
        long = self.preview("base-servo", {})
        equal = self.preview("base-servo", {"horn_profile": 0})
        self.assertEqual((long.status_code, equal.status_code), (200, 200))
        self.assertEqual(long.json()["parameters"]["span"], 33.58)
        self.assertEqual(equal.json()["parameters"]["span"], 26.25)
        self.assertNotEqual(long.json()["mesh"], equal.json()["mesh"])
        for invalid in (0.5, 2, True, "long"):
            response = self.preview("base-servo", {"horn_profile": invalid})
            self.assertEqual(response.status_code, 422)
            self.assertIn("horn_profile", response.json()["detail"]["fields"])

    def test_servo_horn_regenerates_and_rejects_invalid_socket_dimensions(self):
        response = self.preview("servo-horn", {"arm_hole_diameter": 1.4, "clearance": 0.1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parameters"]["clearance"], 0.1)
        for parameters, field in (
            ({"minor_diameter": 4.9}, "minor_diameter"),
            ({"major_diameter": 5.8, "clearance": 0.2}, "major_diameter"),
            ({"depth": 3.5}, "depth"),
        ):
            with self.subTest(field=field):
                response = self.preview("servo-horn", parameters)
                self.assertEqual(response.status_code, 422)
                self.assertIn(field, response.json()["detail"]["fields"])

    def test_shorter_bracket_pin_and_changed_head_bore(self):
        for model in ("bracket", "bracket-print"):
            response = self.preview(model, {"pin_depth": 1.5, "pin_diameter": 3})
            self.assertEqual(response.status_code, 200)
            self.assertAlmostEqual(response.json()["bounds"]["min"][0], -19.5, places=5)
        head = build_head_preview(resolve_fields(HEAD_FIELDS, {"upper_lug_diameter": 2.4}))
        self.assertEqual(self.preview("head-print", {"upper_lug_diameter": 2.4}).status_code, 200)
        _, y, z = HEAD_PARAMETERS.lugs[2].holes[0].center
        self.assertTrue(any(
            face.geom_type == GeomType.CYLINDER and abs(face.radius - 1.2) < 1e-6
            and abs(face.axis_of_rotation.position.Y - y) < 1e-6
            and abs(face.axis_of_rotation.position.Z - z) < 1e-6
            for face in head.faces()
        ))
