import unittest
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from zipfile import ZipFile

from build123d import Mesher, Rot, import_step, import_stl
from fastapi import FastAPI
from fastapi.testclient import TestClient

from argus.models.preview import resolve_fields
from argus.web.api import _MODELS, router


class TestWebExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    def export(self, models, formats):
        return self.client.post("/api/exports", json={"models": models, "formats": formats})

    def test_single_format_downloads_use_the_model_filename(self):
        for extension in ("step", "3mf", "stl"):
            with self.subTest(extension=extension):
                response = self.export([{"id": "bracket-print"}], [extension])
                self.assertEqual(response.status_code, 200, response.text[:300] if response.is_error else "")
                self.assertEqual(
                    response.headers["content-disposition"], f'attachment; filename="gimbal_bracket_print.{extension}"',
                )
                if extension == "step":
                    self.assertTrue(response.content.startswith(b"ISO-10303-21;"))
                elif extension == "3mf":
                    with ZipFile(BytesIO(response.content)) as archive:
                        self.assertIn("3D/3dmodel.model", archive.namelist())
                else:
                    triangle_count = int.from_bytes(response.content[80:84], "little")
                    self.assertGreater(triangle_count, 0)
                    self.assertEqual(len(response.content), 84 + 50 * triangle_count)

    def test_archive_contains_verified_assembly_and_print_geometry(self):
        selections = {"base": {"plate_side": 42}, "head-print": {}}
        builds = {key: Mock(wraps=_MODELS[key].build) for key in selections}
        overrides = {key: replace(_MODELS[key], build=build) for key, build in builds.items()}
        formats = ["step", "3mf", "stl"]
        with patch.dict(_MODELS, overrides):
            response = self.export([{"id": "base", "parameters": selections["base"]}, {"id": "head-print"}], formats)
        self.assertEqual(response.status_code, 200, response.text[:300] if response.is_error else "")
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(response.headers["content-disposition"], 'attachment; filename="argus-models.zip"')
        for key, build in builds.items():
            model = _MODELS[key]
            build.assert_called_once_with(resolve_fields(model.fields, selections[key]))

        with TemporaryDirectory() as directory, ZipFile(BytesIO(response.content)) as archive:
            root = Path(directory)
            self.assertCountEqual(archive.namelist(), [
                f"{_MODELS[key].spec.output_stem}.{extension}" for key in selections for extension in formats
            ])
            archive.extractall(root)
            for key, parameters in selections.items():
                with self.subTest(model=key):
                    model = _MODELS[key]
                    shape = model.build(resolve_fields(model.fields, parameters))
                    stem = model.spec.output_stem
                    placed = shape.moved(model.assembly_pose)
                    reread = import_step(root / f"{stem}.step")
                    self.assertTrue(reread.is_valid)
                    self.assertAlmostEqual(reread.volume, placed.volume, delta=0.01)
                    actual, expected = reread.bounding_box(), placed.bounding_box()
                    self.assertLess((actual.min - expected.min).length, 0.001)
                    self.assertLess((actual.max - expected.max).length, 0.001)

                    print_bounds = (Rot(*model.spec.print_rotation) * shape).bounding_box()
                    mesh_3mf, = Mesher().read(root / f"{stem}.3mf")
                    for mesh in (mesh_3mf, import_stl(root / f"{stem}.stl")):
                        bounds = mesh.bounding_box()
                        self.assertAlmostEqual(bounds.min.Z, 0, delta=0.02)
                        self.assertAlmostEqual(bounds.center().X, 0, delta=0.05)
                        self.assertAlmostEqual(bounds.center().Y, 0, delta=0.05)
                        self.assertLess((bounds.size - print_bounds.size).length, 0.05)

    def test_invalid_requests_and_failed_writes_return_no_download(self):
        base = {"id": "base"}
        for models, formats, status in (
            ([], ["step"], 422), ([base], [], 422), ([base], ["obj"], 422),
            ([base, base], ["step"], 422), ([base], ["step", "step"], 422),
            ([{"id": "missing"}], ["step"], 404),
        ):
            with self.subTest(models=models, formats=formats):
                response = self.export(models, formats)
                self.assertEqual(response.status_code, status)
                self.assertNotIn("content-disposition", response.headers)
        response = self.export([{"id": "base", "parameters": {"plate_side": 34, "corner_hole_pitch": 32}}], ["step"])
        self.assertEqual(response.status_code, 422)
        self.assertIn("corner_hole_pitch", response.json()["detail"]["fields"])

        staging = []

        def fail_write(_shape, path, **_options):
            staging.append(path.parent)
            self.assertTrue((path.parent / "gimbal_base.step").is_file())
            path.write_bytes(b"partial STL")
            raise OSError("writer failed")

        with patch("argus.exporting._write_stl", side_effect=fail_write), self.assertLogs("argus.web.api", "ERROR"):
            response = self.export([base], ["step", "stl"])
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("content-disposition", response.headers)
        self.assertEqual(response.json()["detail"], {
            "message": "底座的 STL 导出失败，请重试。", "model": "base", "format": "stl",
        })
        self.assertEqual(len(staging), 1)
        self.assertFalse(staging[0].exists())
