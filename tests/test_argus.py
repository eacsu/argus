import os
import unittest
from contextlib import chdir
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from build123d import Compound, Face, GeomType, Location, Mesher, Plane, Pos, Rot, Solid, Vector, export_step, import_step, section
from typer.testing import CliRunner

from argus.assembly import BASE, BRACKET, PARTS
from argus.commands.app import app
from argus.models.base import build_base
from argus.models.base.parameters import BASE_PARAMETERS
from argus.models.bracket import build_bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS
from argus.models.bracket_print import build_print_bracket
from argus.models.head import build_head
from argus.models.head.parameters import HEAD_PARAMETERS
from argus.models.head_print import build_print_head
from argus.workflow import export_reference_parts


SOURCE = Path(__file__).resolve().parents[1] / "data-bin" / "舵机云台总装.step"


def step_label(label):
    return b"'\\X2\\" + label.encode("utf-16-be").hex().upper().encode("ascii") + b"\\X0\\'"


def write_assembly(path, parts):
    labels = {}
    for index, part in enumerate(parts):
        alias = f"argus_test_part_{index}"
        labels[alias] = part.label
        part.label = alias
    if not export_step(Compound(children=parts, label="Argus test assembly"), path):
        raise AssertionError("测试用 STEP 导出失败")
    # OCCT's STEP writer can emit raw UTF-8 labels. Write the STEP Unicode
    # escapes explicitly so the reader sees the same labels as the real input.
    data = path.read_bytes()
    for alias, original in labels.items():
        data = data.replace(f"'{alias}'".encode("ascii"), step_label(original))
    path.write_bytes(data)


class TestArgus(unittest.TestCase):
    def invoke(self, source, output):
        return CliRunner().invoke(app, ["--source", str(source), "--output-dir", str(output)])

    def test_missing_input_keeps_previous_exports(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / "gimbal_base.step"
            previous.write_bytes(b"previous export")
            result = self.invoke(root / "missing.step", root)
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("找不到装配 STEP", result.output)
            self.assertEqual(previous.read_bytes(), b"previous export")

    def test_missing_component_is_reported(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "missing_component.step"
            part = Solid.make_box(10, 10, 10)
            part.label = BASE.source_label
            write_assembly(fixture, [part])
            result = self.invoke(fixture, root / "output")
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("「舵机云台-1」应有一件，实际找到 0 件", result.output)

    def test_main_exports_all_three_parts_without_source(self):
        runner = CliRunner()
        with (
            TemporaryDirectory() as directory,
            chdir(directory),
            patch.dict(os.environ),
            patch("argus.workflow.read_structural_parts") as read_source,
        ):
            os.environ.pop("ARGUS_SOURCE", None)
            output = Path("exports")
            result = runner.invoke(app, ["--output-dir", str(output)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(len(list(output.iterdir())), 6)
            for spec in PARTS:
                name = spec.output_stem
                with self.subTest(part=name):
                    exported = import_step(output / f"{name}.step")
                    self.assertEqual(len(exported.solids()), 1)
                    self.assertTrue(exported.is_valid)
                    reader = Mesher()
                    meshes = reader.read(output / f"{name}.3mf")
                    self.assertEqual(len(meshes), 1)
                    self.assertGreater(reader.triangle_counts[0], 0)
                    self.assertAlmostEqual(meshes[0].bounding_box().min.Z, 0, delta=0.02)
            read_source.assert_not_called()

    def test_base_plate_and_bores_are_quarter_turn_symmetric_about_ring(self):
        part = build_base(BASE_PARAMETERS)
        bounds = part.bounding_box()
        ring_x, ring_y = BASE_PARAMETERS.ring.center
        self.assertAlmostEqual(bounds.center().X, ring_x)
        self.assertAlmostEqual(bounds.center().Y, ring_y)
        self.assertAlmostEqual(bounds.size.X, 38)
        self.assertAlmostEqual(bounds.size.Y, 38)
        turn = Pos(ring_x, ring_y, 0) * Rot(0, 0, 90) * Pos(-ring_x, -ring_y, 0)
        for height in (0.3, 1.75):
            with self.subTest(height=height):
                profile = section(part, section_by=Plane((0, 0, height)))
                self.assertEqual(len(profile.faces()), 1)
                self.assertEqual(len(profile.faces()[0].inner_wires()), 8)
                rotated = turn * profile
                for a, b in ((profile, rotated), (rotated, profile)):
                    self.assertLess(sum(face.area for face in a.cut(b).faces()), 1e-6)

    def test_print_bracket_fills_the_underside_and_preserves_clearances(self):
        parameters = BRACKET_PARAMETERS
        original = build_bracket(parameters)
        printed = build_print_bracket(parameters)
        self.assertTrue(printed.is_valid)
        self.assertEqual(len(printed.solids()), 1)
        self.assertGreater(printed.volume, original.volume)
        self.assertLess(sum(solid.volume for solid in original.cut(printed).solids()), 1e-6)
        self.assertLess((printed.bounding_box().size - original.bounding_box().size).length, 1e-6)

        # Cross-sections at the bed and farther into the two arms share the same flat bottom.
        bottom = original.bounding_box().min.Z
        for y, x in ((0.05, 10), (18, 16.75), (26, 16.75)):
            for sign in (-1, 1):
                point = (sign * x, y, bottom + 0.2)
                self.assertFalse(original.is_inside(point))
                self.assertTrue(printed.is_inside(point))

        for y in (0.05, 7.0):
            for x in (-8, 0, 8):
                self.assertTrue(printed.is_inside((x, y, bottom + 0.2)))

        shaft_y, shaft_z = parameters.shaft_axis
        for point in (
            (0, 2.5, -18), (0, 18, bottom + 0.2), (16.75, 20, -26),
            (-16.75, 20, -26), (16.75, shaft_y - 1, shaft_z),
        ):
            self.assertFalse(printed.is_inside(point))

    def test_print_head_flattens_lower_features_and_preserves_mounting_clearances(self):
        original = build_head(HEAD_PARAMETERS)
        printed = build_print_head(HEAD_PARAMETERS)
        self.assertTrue(printed.is_valid)
        self.assertEqual(len(printed.solids()), 1)
        self.assertLess(sum(solid.volume for solid in original.cut(printed).solids()), 1e-6)
        self.assertLess((printed.bounding_box().size - original.bounding_box().size).length, 1e-6)

        bottom = original.bounding_box().min.Z
        for x, y in ((-19.5, 1), (19.5, 1), (-18.3, 8), (16, 8), (0, 3)):
            point = (x, y, bottom + 0.2)
            self.assertFalse(original.is_inside(point))
            self.assertTrue(printed.is_inside(point))
        self.assertFalse(printed.is_inside((0, 8, bottom + 0.2)))

        for x in (-15, 13):
            for y in (0.25, 1, 1.75):
                self.assertFalse(printed.is_inside((x, y, -2)))

    def test_print_variants_have_their_own_exports(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ),
            patch("argus.workflow.read_structural_parts") as read_source,
        ):
            os.environ.pop("ARGUS_SOURCE", None)
            output = Path(directory) / "exports"
            for model in ("bracket", "head"):
                with self.subTest(model=model):
                    target = output / model
                    result = CliRunner().invoke(app, [f"--{model}-print", "--output-dir", str(target)])
                    self.assertEqual(result.exit_code, 0, result.output)
                    self.assertEqual({path.name for path in target.iterdir()}, {
                        f"gimbal_{model}_print.step", f"gimbal_{model}_print.3mf",
                    })
            read_source.assert_not_called()

    def test_python_dimensions_change_base_geometry(self):
        center_x, center_y = 1.5, -3.0
        parameters = replace(
            BASE_PARAMETERS,
            ring=replace(BASE_PARAMETERS.ring, center=(center_x, center_y)),
            plate_thickness=4,
            corner_holes=replace(BASE_PARAMETERS.corner_holes, offset=(14, 14), radius=1.45),
        )
        part = build_base(parameters)
        self.assertTrue(part.is_valid)
        bounds = part.bounding_box()
        self.assertAlmostEqual(bounds.size.Z, 13, places=5)
        self.assertAlmostEqual(bounds.center().X, center_x)
        self.assertAlmostEqual(bounds.center().Y, center_y)
        centers = {
            (round(face.axis_of_rotation.position.X, 5), round(face.axis_of_rotation.position.Y, 5))
            for face in part.faces()
            if face.geom_type == GeomType.CYLINDER
            and abs(face.axis_of_rotation.direction.Z) > 0.999
            and abs(face.radius - 1.45) < 1e-5
        }
        self.assertEqual(centers, {(center_x + x, center_y + y) for x in (-14, 14) for y in (-14, 14)})

    def test_bracket_mirrors_shared_features_after_dimension_changes(self):
        parameters = replace(BRACKET_PARAMETERS, window_width=18, window_height=26, arm_thickness=2.75)
        part = build_bracket(parameters)
        self.assertTrue(part.is_valid)
        self.assertEqual(len(part.solids()), 1)

        front = section(part, section_by=Plane((0, 2.5, 0), z_dir=(0, 1, 0))).faces()[0]
        self.assertEqual(len(front.inner_wires()), 1)
        window = front.inner_wires()[0].bounding_box()
        self.assertAlmostEqual(window.center().X, 0)
        self.assertAlmostEqual(window.center().Z, -parameters.frame_height / 2)
        self.assertAlmostEqual(window.size.X, parameters.window_width)
        self.assertAlmostEqual(window.size.Z, parameters.window_height)

        arm_mid_x = 18 - parameters.arm_thickness / 2
        left, right = (
            section(part, section_by=Plane((x, 0, 0), z_dir=(1, 0, 0))).faces()[0]
            for x in (-arm_mid_x, arm_mid_x)
        )
        self.assertEqual(len(left.inner_wires()), 1)
        self.assertEqual(len(right.inner_wires()), 3)
        right_opening, = [wire for wire in right.inner_wires() if len(wire.edges()) > 1]
        for left_wire, right_wire in (
            (left.outer_wire(), right.outer_wire()), (left.inner_wires()[0], right_opening),
        ):
            mirrored, target = Face(left_wire).mirror(Plane.YZ), Face(right_wire)
            for a, b in ((mirrored, target), (target, mirrored)):
                self.assertLess(sum(face.area for face in a.cut(b).faces()), 1e-6)

        for x in (-11.5, 11.5):
            for z in (-29.5, -9.5):
                self.assertTrue(part.is_inside((x, 6.5, z)))
            self.assertFalse(part.is_inside((x, 6.5, -19.5)))

    @unittest.skipUnless(SOURCE.is_file(), "本地没有原装配 STEP")
    def test_reference_exports_preserve_source_geometry_and_pose(self):
        assembly = import_step(SOURCE)
        source_parts = {part.label: part for part in assembly.children}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "structural-parts"
            export_reference_parts(SOURCE, output)
            self.assertEqual(
                {p.name for p in output.iterdir()},
                {f"{spec.output_stem}.{ext}" for spec in PARTS for ext in ("step", "3mf")},
            )
            for spec in PARTS:
                with self.subTest(part=spec.output_stem):
                    original = source_parts[spec.source_label]
                    exported = import_step(output / f"{spec.output_stem}.step")
                    self.assertEqual(len(exported.solids()), 1)
                    self.assertTrue(exported.is_valid)
                    self.assertAlmostEqual(exported.volume, original.volume, delta=1e-4)
                    actual, expected = exported.bounding_box(), original.bounding_box()
                    self.assertLess((actual.min - expected.min).length, 1e-5)
                    self.assertLess((actual.max - expected.max).length, 1e-5)

    @unittest.skipUnless(SOURCE.is_file(), "本地没有原装配 STEP")
    def test_changed_hole_and_pose_are_used_and_failed_fit_keeps_exports(self):
        assembly = import_step(SOURCE)
        parts = []
        labels = {spec.source_label for spec in PARTS}
        for part in reversed(assembly.children):
            if part.label not in labels:
                continue
            if part.label == BASE.source_label:
                bore = Solid.make_cylinder(1.45, 7, Plane((15, 15, -1)))
                new_base = part.located(Location()).cut(bore)
                new_base.label = BASE.source_label
                new_base.location = Pos(0.8, 0.2, -0.4) * part.location
                parts.append(new_base)
            else:
                parts.append(part)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture, output = root / "changed.step", root / "output"
            write_assembly(fixture, parts)
            result = self.invoke(fixture, output)
            self.assertEqual(result.exit_code, 0, result.output)
            ref = next(part for part in import_step(fixture).children if part.label == BASE.source_label)
            fitted = import_step(output / "gimbal_base.step")
            self.assertLess((fitted.bounding_box().min - ref.bounding_box().min).length, 0.001)
            fitted = fitted.moved(ref.location.inverse())
            changed_radii = [
                face.radius for face in fitted.faces()
                if face.geom_type == GeomType.CYLINDER
                and abs(face.axis_of_rotation.direction.Z) > 0.999
                and (face.axis_of_rotation.position - Vector(15, 15, 0)).cross(Vector(0, 0, 1)).length < 1e-5
            ]
            self.assertEqual(len(changed_radii), 1)
            self.assertAlmostEqual(changed_radii[0], 1.45, places=5)

            before = {file.name: file.read_bytes() for file in output.iterdir()}
            broken = root / "broken.step"
            broken_parts = list(import_step(fixture).children)
            replacement = Solid.make_box(10, 10, 10)
            bracket = next(index for index, part in enumerate(broken_parts) if part.label == BRACKET.source_label)
            replacement.label = broken_parts[bracket].label
            broken_parts[bracket] = replacement
            write_assembly(broken, broken_parts)
            failure = self.invoke(broken, output)
            self.assertEqual(failure.exit_code, 1, failure.output)
            self.assertIn("拟合失败", failure.output)
            self.assertEqual({file.name: file.read_bytes() for file in output.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
