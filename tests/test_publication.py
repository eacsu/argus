import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

from argus.workflow import publish


NAMES = tuple(
    f"gimbal_{part}.{extension}"
    for part in ("bracket", "base", "head")
    for extension in ("step", "3mf")
)


def stage_batch(root, content):
    root.mkdir()
    paths = [root / name for name in NAMES]
    for path in paths:
        path.write_text(content, encoding="ascii")
    return paths


class TestPublication(unittest.TestCase):
    def test_same_output_directory_serializes_complete_batches(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output, staging_a, staging_b = (root / name for name in ("exports", "a", "b"))
            a = stage_batch(staging_a, "a")
            b = stage_batch(staging_b, "b")
            a_replaced_first, allow_a, b_started, b_replaced_first = (Event() for _ in range(4))
            replace = Path.replace

            def hold_first_batch(path, target):
                replaced = replace(path, target)
                if path == a[0]:
                    a_replaced_first.set()
                    if not allow_a.wait(5):
                        raise TimeoutError("first publication did not resume")
                if path == b[0]:
                    b_replaced_first.set()
                return replaced

            def publish_b():
                b_started.set()
                publish(root / "a" / ".." / output.name, b, staging_b)

            with patch.object(Path, "replace", hold_first_batch), ThreadPoolExecutor(2) as pool:
                first = pool.submit(publish, output, a, staging_a)
                try:
                    self.assertTrue(a_replaced_first.wait(5))
                    second = pool.submit(publish_b)
                    self.assertTrue(b_started.wait(5))
                    self.assertFalse(b_replaced_first.wait(0.2))
                finally:
                    allow_a.set()
                first.result(timeout=5)
                second.result(timeout=5)

            self.assertEqual(
                {path.name: path.read_text(encoding="ascii") for path in output.iterdir()},
                dict.fromkeys(NAMES, "b"),
            )

    def test_publish_error_rolls_back_replaced_and_created_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output, staging = root / "exports", root / "staging"
            output.mkdir()
            (output / NAMES[0]).write_text("previous", encoding="ascii")
            files = stage_batch(staging, "new")
            replace = Path.replace

            def fail_last_write(path, target):
                if path == files[-1]:
                    raise OSError("injected publish failure")
                return replace(path, target)

            with patch.object(Path, "replace", fail_last_write):
                with self.assertRaisesRegex(OSError, "injected publish failure"):
                    publish(output, files, staging)
            self.assertEqual(
                {path.name: path.read_text(encoding="ascii") for path in output.iterdir()},
                {NAMES[0]: "previous"},
            )
