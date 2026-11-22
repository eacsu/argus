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
from argus.exporting import stage_assembly
from argus.models.base import build_base
from argus.models.base.parameters import BASE_PARAMETERS, BASE_POSE
from argus.models.base_servo import build_servo_base
from argus.models.base_servo.parameters import HORN_PARAMETERS, LONG_HORN_SEAT, LONG_SERVO_BASE_PARAMETERS, SERVO_BASE_PARAMETERS, HornProfile
from argus.models.base_split import BaseConnection
from argus.models.base_split.parameters import default_base
from argus.models.bracket import build_bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS
from argus.models.bracket_print import build_print_bracket
from argus.models.common import X, Prism, box_at, cylinder
from argus.models.gimbal import gimbal_parts
from argus.models.head import build_head
from argus.models.head.parameters import HEAD_PARAMETERS
from argus.models.head_print import build_print_head
from argus.models.servo_horn import build_servo_horn, horn_outline
from argus.models.servo_horn.parameters import LONG_HORN_PARAMETERS, SERVO_HORN_PARAMETERS
from argus.models.servo_horn.single import SINGLE_HORN, build_single_horn, outline as single_horn_outline
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

    def test_main_exports_default_base_and_horn_with_structure_without_source(self):
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
            self.assertEqual(len(list(output.iterdir())), 14)
            for name in ("gimbal_base_lower", "gimbal_base_upper", "gimbal_bracket", "gimbal_head", "servo_horn_long", "servo_horn_single"):
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

    def test_split_base_holds_both_horns_and_the_m3_screws_are_recessed(self):
        for profile in HornProfile:
            with self.subTest(profile=profile):
                base = default_base(profile, BaseConnection.M3)
                parts = gimbal_parts(profile, base)
                lower, upper, horn, servo = [part.local_shape.moved(BASE_POSE.inverse() * part.assembly_pose) for part in parts[:4]]
                for first, second in ((lower, upper), (lower, horn), (upper, horn), (lower, servo), (upper, servo), (horn, servo)):
                    self.assertLess(sum(shape.volume for shape in first.intersect(second) or []), 1e-5)
                hardware = base.fasteners
                reach = hardware.thread_reach(base.lower_thickness)
                for index, (x, y) in enumerate(base.bolt_centers()):
                    bolt, insert = [part.local_shape.moved(BASE_POSE.inverse() * part.assembly_pose)
                                    for part in parts[8 + 2 * index:10 + 2 * index]]
                    self.assertGreater(bolt.bounding_box().min.Z, 0)
                    self.assertAlmostEqual(bolt.bounding_box().max.Z, base.lower_thickness + reach)
                    self.assertAlmostEqual(insert.bounding_box().min.Z, base.lower_thickness)
                    self.assertGreaterEqual(reach, hardware.insert_length)
                    self.assertLess(reach, hardware.pilot_depth)
                    self.assertFalse(lower.is_inside((x + 2.5, y, 1)))
                    self.assertTrue(lower.is_inside((x + 2.5, y, 4)))
                    self.assertFalse(upper.is_inside((x + 1.9, y, base.lower_thickness + 1)))
                    self.assertTrue(upper.is_inside((x, y, base.lower_thickness + 4.5)))
                    for layer in (lower, upper):
                        self.assertLess(sum(shape.volume for shape in bolt.intersect(layer) or []), 1e-5)

    def test_default_snap_base_captures_each_horn_and_blocks_a_straight_pull(self):
        for profile in HornProfile:
            with self.subTest(profile=profile):
                base = default_base(profile)
                parts = gimbal_parts(profile, base)
                self.assertEqual(len(parts), 8)
                self.assertEqual(parts[1].spec.print_rotation, (180, 0, 0))
                lower, upper, horn, servo = [part.local_shape.moved(BASE_POSE.inverse() * part.assembly_pose) for part in parts[:4]]
                for layer in (lower, upper):
                    self.assertTrue(layer.is_valid)
                    self.assertEqual(len(layer.solids()), 1)
                for first, second in ((lower, upper), (lower, horn), (upper, horn), (lower, servo), (upper, servo)):
                    self.assertLess(sum(shape.volume for shape in first.intersect(second) or []), 1e-5)
                lifted = upper.moved(Pos(0, 0, 0.5))
                self.assertGreater(sum(shape.volume for shape in lower.intersect(lifted) or []), 2.0)

                snap = base.snap_fit
                engagement = snap.hook_outer - snap.stem_outer - snap.clearance
                travel = engagement + 0.05
                self.assertGreater(snap.inward_travel, travel)
                released_hook = box_at(
                    (snap.stem_inner - travel, snap.hook_start, -snap.tip_depth),
                    (snap.hook_outer - snap.stem_inner, snap.hook_end - snap.hook_start, snap.tip_depth + 1),
                )
                for rim, _ in snap._placements(base.center, base.plate_side, base.lower_thickness):
                    sweep = rim * released_hook
                    self.assertLess(sum(shape.volume for shape in lower.intersect(sweep) or []), 1e-5)

    def test_assembly_step_retains_every_named_occurrence(self):
        with TemporaryDirectory() as directory:
            for connection, count in ((BaseConnection.SNAP, 8), (BaseConnection.M3, 16)):
                with self.subTest(connection=connection):
                    parts = gimbal_parts(HornProfile.EQUAL, default_base(HornProfile.EQUAL, connection))
                    path = stage_assembly(parts, Path(directory) / f"gimbal_{connection}.step")
                    children = import_step(path).children
                    self.assertEqual(len(children), count)
                    self.assertCountEqual([child.label for child in children], [part.spec.output_stem for part in parts])

    def test_single_horn_fits_both_brackets_and_the_upper_output_shaft(self):
        horn = build_single_horn()
        dimensions = horn.bounding_box().size
        for actual, expected in zip(dimensions, (21.3, 6.76, 4.82)):
            self.assertAlmostEqual(actual, expected)
        holes = SINGLE_HORN.arm_holes()
        self.assertAlmostEqual(holes[-1] - holes[-2], 2.43)
        p = BRACKET_PARAMETERS
        installed = p.horn_seat.horn_pose(p.right_arm_x, p.shaft_axis)
        distal = (installed * Pos(holes[-2], 0, 0)).position
        stroke = SINGLE_HORN.overall_height + p.horn_seat.pocket_depth + 1
        arm_sweep = Solid.extrude(Face(single_horn_outline(SINGLE_HORN)), (0, 0, -stroke)).moved(
            installed * Pos(0, 0, SINGLE_HORN.arm_thickness),
        )
        hub_start = (installed * Pos(0, 0, SINGLE_HORN.overall_height)).position
        hub_sweep = cylinder(SINGLE_HORN.hub_diameter / 2, hub_start, X, stroke)
        for builder in (build_bracket, build_print_bracket):
            with self.subTest(bracket=builder.__name__):
                part = builder(p)
                self.assertTrue(part.is_valid)
                self.assertFalse(part.is_inside((17, distal.Y, distal.Z)))
                self.assertFalse(part.is_inside((17, *p.shaft_axis)))
                for sweep in (arm_sweep, hub_sweep):
                    self.assertLess(sum(s.volume for s in part.intersect(sweep) or []), 1e-6)

        parts = gimbal_parts(HornProfile.LONG, default_base(HornProfile.LONG))
        shapes = {part.spec.output_stem: part.local_shape.moved(part.assembly_pose) for part in parts}
        installed_horn = shapes["servo_horn_single"]
        self.assertLess(sum(s.volume for s in installed_horn.intersect(shapes["sg90s_top"]) or []), 1e-6)

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

    def test_servo_base_has_two_seating_depths_and_symmetric_through_holes(self):
        base, horn = SERVO_BASE_PARAMETERS, HORN_PARAMETERS
        part = build_servo_base(base, horn)
        self.assertTrue(part.is_valid)
        self.assertEqual(len(part.solids()), 1)
        bounds = part.bounding_box()
        x, y = base.ring.center
        self.assertAlmostEqual(bounds.size.X, 42)
        self.assertAlmostEqual(bounds.size.Y, 42)
        self.assertAlmostEqual(bounds.max.Z, BASE_PARAMETERS.plate_thickness + BASE_PARAMETERS.ring.height, places=5)
        turn = Pos(x, y, 0) * Rot(0, 0, 90) * Pos(-x, -y, 0)
        self.assertLess(sum(solid.volume for solid in part.cut(turn * part).solids()), 1e-6)

        arm_floor = base.plate_thickness - horn.arm_depth
        hub_floor = base.plate_thickness - horn.hub_depth
        profile = section(part, section_by=Plane((0, 0, arm_floor + 0.1)))
        pocket = max(profile.faces()[0].inner_wires(), key=lambda wire: wire.length)
        self.assertAlmostEqual(pocket.bounding_box().size.X, horn.envelope.main_arm.span + 2 * horn.clearance)
        self.assertAlmostEqual(pocket.bounding_box().size.Y, horn.envelope.main_arm.span + 2 * horn.clearance)
        for offset, depth in ((6, arm_floor), (2.5, hub_floor)):
            self.assertTrue(part.is_inside((x + offset, y, depth - 0.01)))
            self.assertFalse(part.is_inside((x + offset, y, depth + 0.01)))
        for dx, dy in ((0.0, 0.0), *horn.mounting_offsets()):
            self.assertFalse(part.is_inside((x + dx, y + dy, 1.0)))

    def test_servo_horn_has_symmetric_holes_and_can_drop_into_base(self):
        parameters = SERVO_HORN_PARAMETERS
        envelope = parameters.envelope
        horn = build_servo_horn(parameters)
        self.assertTrue(horn.is_valid)
        self.assertEqual(len(horn.solids()), 1)
        bounds = horn.bounding_box()
        self.assertAlmostEqual(bounds.size.X, 26.25)
        self.assertAlmostEqual(bounds.size.Y, 26.25)
        self.assertAlmostEqual(bounds.size.Z, 3.96)

        profile = section(horn, section_by=Plane((0, 0, 0.5)))
        holes = profile.faces()[0].inner_wires()
        self.assertEqual(len(holes), 13)
        expected = [(0, 0, 2.1)]
        for offset in (5.8, 8.3, 10.8):
            expected.extend((x, y, 1.2) for x, y in ((offset, 0), (0, offset), (-offset, 0), (0, -offset)))
        actual = []
        for wire in holes:
            box = wire.bounding_box()
            x, y, _ = box.center()
            actual.append(tuple(round(value, 5) for value in (x, y, box.size.X)))
        self.assertCountEqual(actual, expected)

        self.assertLess(sum(solid.volume for solid in horn.cut(Rot(0, 0, 90) * horn).solids()), 1e-6)
        base = build_servo_base(SERVO_BASE_PARAMETERS, HORN_PARAMETERS)
        x, y = SERVO_BASE_PARAMETERS.ring.center
        seat = SERVO_BASE_PARAMETERS.plate_thickness - HORN_PARAMETERS.arm_depth
        insertion = Prism(horn_outline(envelope, (x, y), seat), (0, 0, base.bounding_box().max.Z)).build()
        self.assertLess(sum(solid.volume for solid in base.intersect(insertion) or []), 1e-6)
        for dx, dy in ((8.3, 0), (0, 8.3), (-8.3, 0), (0, -8.3)):
            self.assertFalse(base.is_inside((x + dx, y + dy, seat - 0.5)))

    def test_long_horn_has_matching_arm_pairs_and_fits_its_base(self):
        horn = build_servo_horn(LONG_HORN_PARAMETERS)
        bounds = horn.bounding_box()
        self.assertTrue(horn.is_valid)
        self.assertEqual(len(horn.solids()), 1)
        for dimension, expected in zip(bounds.size, (19.8, 33.58, 4.62)):
            self.assertAlmostEqual(dimension, expected)
        profile = section(horn, section_by=Plane((0, 0, 0.5)))
        self.assertEqual(len(profile.faces()[0].inner_wires()), 19)
        self.assertLess(sum(solid.volume for solid in horn.cut(Rot(0, 0, 180) * horn).solids()), 1e-6)

        base = build_servo_base(LONG_SERVO_BASE_PARAMETERS, LONG_HORN_SEAT)
        self.assertTrue(base.is_valid)
        self.assertEqual(len(base.solids()), 1)
        x, y = LONG_SERVO_BASE_PARAMETERS.ring.center
        seat = LONG_SERVO_BASE_PARAMETERS.plate_thickness - LONG_HORN_SEAT.arm_depth
        insertion = Prism(horn_outline(LONG_HORN_PARAMETERS.envelope, (x, y), seat), (0, 0, 14)).build()
        self.assertLess(sum(solid.volume for solid in base.intersect(insertion) or []), 1e-6)
        for dx, dy in ((7.73, 0), (0, 12.97), (-7.73, 0), (0, -12.97)):
            self.assertFalse(base.is_inside((x + dx, y + dy, 2)))
            self.assertFalse(horn.is_inside((dx, dy, 1)))

    @unittest.skipUnless(SOURCE.is_file(), "没有用于验证花键的参考装配")
    def test_servo_horn_socket_engages_reference_shaft(self):
        parameters = SERVO_HORN_PARAMETERS
        horn = build_servo_horn(parameters)
        x, y = BASE_PARAMETERS.ring.center
        reference = import_step(SOURCE)
        servo = next(node for node in reference.children if node.label == "servo-1").moved(BASE_POSE.inverse())
        floor = parameters.envelope.overall_height - parameters.socket.depth
        installed = servo.moved(Pos(-x, -y, floor - servo.bounding_box().min.Z))
        self.assertLess(sum(solid.volume for solid in horn.intersect(installed) or []), 1e-6)
        half_tooth = Rot(0, 0, 180 / parameters.socket.teeth) * installed
        self.assertGreater(sum(solid.volume for solid in horn.intersect(half_tooth) or []), 0.1)
        self.assertFalse(horn.is_inside((0, 0, floor / 2)))
        self.assertTrue(horn.is_inside((1.5, 0, floor / 2)))

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
