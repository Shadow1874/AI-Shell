import tempfile
import unittest
from pathlib import Path

from core.file_reader import build_file_context, extract_file_text


class FileReaderTests(unittest.TestCase):
    def test_reads_utf8_text_file(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "sample.txt"
            file_path.write_text("Привет, мир!", encoding="utf-8")
            self.assertEqual(extract_file_text(str(file_path)), "Привет, мир!")

    def test_builds_context_with_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "notes.md"
            file_path.write_text("Тестовый текст", encoding="utf-8")
            context = build_file_context([str(file_path)])
            self.assertIn("notes.md", context)
            self.assertIn("Тестовый текст", context)

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "sample.unknown"
            file_path.write_text("data", encoding="utf-8")
            with self.assertRaises(ValueError):
                extract_file_text(str(file_path))


if __name__ == "__main__":
    unittest.main()
