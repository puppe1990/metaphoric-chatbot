from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import convert_books_to_markdown as sut


class ConvertBooksToMarkdownTests(unittest.TestCase):
    def test_convert_file_uses_python_fallback_for_mobi(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.mobi"
            source.write_bytes(b"fake-mobi")
            output_dir = root / "markdown"
            output_dir.mkdir()

            extracted_dir = root / "extracted"
            extracted_dir.mkdir()
            extracted_file = extracted_dir / "book.html"
            extracted_file.write_text("<h1>Title</h1><p>Hello</p>", encoding="utf-8")

            fake_converter = SimpleNamespace(
                convert=lambda path: SimpleNamespace(markdown=f"converted from {Path(path).suffix}")
            )

            with patch.object(sut.mobi, "extract", return_value=(str(extracted_dir), str(extracted_file))):
                result = sut.convert_file(fake_converter, source, output_dir, overwrite=True)

            self.assertEqual(result.status, "converted")
            self.assertEqual((output_dir / "sample.md").read_text(encoding="utf-8"), "converted from .html")
            self.assertIn("python-fallback", result.detail)

    def test_convert_file_uses_python_fallback_for_azw3(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.azw3"
            source.write_bytes(b"fake-azw3")
            output_dir = root / "markdown"
            output_dir.mkdir()

            extracted_dir = root / "extracted"
            extracted_dir.mkdir()
            extracted_file = extracted_dir / "book.epub"
            extracted_file.write_text("fake-epub", encoding="utf-8")

            fake_converter = SimpleNamespace(
                convert=lambda path: SimpleNamespace(markdown=f"converted from {Path(path).suffix}")
            )

            with patch.object(sut.mobi, "extract", return_value=(str(extracted_dir), str(extracted_file))):
                result = sut.convert_file(fake_converter, source, output_dir, overwrite=True)

            self.assertEqual(result.status, "converted")
            self.assertEqual((output_dir / "sample.md").read_text(encoding="utf-8"), "converted from .epub")
            self.assertIn("python-fallback", result.detail)


if __name__ == "__main__":
    unittest.main()
