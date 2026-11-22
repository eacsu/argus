"""Export the three structural components from the reference STEP assembly."""

from pathlib import Path

from build123d import Compound, GeomType, Location, Mesher, Pos, Rot, export_step, import_step

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-bin" / "舵机云台总装.step"
OUTPUT = ROOT / "model-bin" / "structural-parts"
PARTS = {
    "舵机云台-1": "gimbal_bracket",
    "舵机云台底座-1": "gimbal_base",
    "舵机云台头-1": "gimbal_head",
}


# Rotations in each part's own coordinate system.
PRINT_ROTATIONS = {
    "gimbal_bracket": (90, 0, 0),  # local -Y: mounting face
    "gimbal_base": (0, 0, 0),      # local -Z: square base plate
    "gimbal_head": (0, 90, 0),     # local +X: largest flat exterior face
}


def main():
    assembly = import_step(SOURCE)
    components = {component.label: component for component in assembly.children}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for label, filename in PARTS.items():
        part = components[label]
        part.label = filename
        step_path = OUTPUT / f"{filename}.step"
        mesh_path = OUTPUT / f"{filename}.3mf"

        if not export_step(Compound(children=[part], label=filename), step_path):
            raise RuntimeError(f"STEP export failed: {label}")
        checked = import_step(step_path)
        bounds = part.bounding_box()
        checked_bounds = checked.bounding_box()
        if (
            len(checked.solids()) != 1
            or not checked.is_valid
            or abs(checked.volume - part.volume) > 1e-4
            or (checked_bounds.min - bounds.min).length > 1e-5
            or (checked_bounds.max - bounds.max).length > 1e-5
        ):
            raise RuntimeError(f"STEP geometry differs from source: {label}")

        oriented = Rot(*PRINT_ROTATIONS[filename]) * part.located(Location())
        print_bounds = oriented.bounding_box()
        center = print_bounds.center()
        printable = Pos(-center.X, -center.Y, -print_bounds.min.Z) * oriented
        contact_area = sum(
            face.area
            for face in printable.faces()
            if face.geom_type == GeomType.PLANE
            and face.normal_at().Z < -0.999
            and abs(face.center().Z) < 1e-5
        )
        if contact_area <= 0:
            raise RuntimeError(f"No flat bed contact: {label}")
        mesher = Mesher()
        mesher.add_shape(printable, linear_deflection=0.01, angular_deflection=0.1)
        mesher.write(mesh_path)
        reader = Mesher()
        meshes = reader.read(mesh_path)
        if len(meshes) != 1 or reader.triangle_counts[0] <= 0:
            raise RuntimeError(f"3MF mesh cannot be read: {label}")
        mesh_bounds = meshes[0].bounding_box()
        if abs(mesh_bounds.min.Z) > 0.03 or (mesh_bounds.size - print_bounds.size).length > 0.05:
            raise RuntimeError(f"3MF dimensions differ from source: {label}")
        print(f"{filename}: STEP volume {checked.volume:.2f} mm^3, 3MF triangles {reader.triangle_counts[0]}, bed contact {contact_area:.2f} mm^2, height {mesh_bounds.size.Z:.2f} mm")


if __name__ == "__main__":
    main()



