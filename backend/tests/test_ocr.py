from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr import OcrResult, extract_text_from_file_path, extract_text_from_pdf_path


@pytest.fixture
def mock_pdf_path(tmp_path):
    p = tmp_path / "test.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    return p


@pytest.fixture
def mock_image_path(tmp_path):
    p = tmp_path / "test.png"
    p.write_bytes(b"fake image content")
    return p


def test_extract_text_native_pdf(mock_pdf_path):
    """Test when pypdf successfully extracts text."""
    with (
        patch("app.services.ocr.PdfReader") as mock_reader_class,
        patch("app.services.ocr.convert_from_path") as mock_convert,
        patch("app.services.ocr.image_to_string") as mock_ocr,
    ):
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Hello from pypdf"
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        result = extract_text_from_pdf_path(mock_pdf_path)

        assert "Hello from pypdf" in result.text
        assert result.page_count == 1
        mock_convert.assert_not_called()
        mock_ocr.assert_not_called()


def test_extract_text_scanned_pdf(mock_pdf_path):
    """Test when pypdf fails (empty text) and falls back to Tesseract."""
    with (
        patch("app.services.ocr.PdfReader") as mock_reader_class,
        patch("app.services.ocr.shutil.which", return_value="/usr/bin/fake"),
        patch("app.services.ocr.convert_from_path") as mock_convert,
        patch("app.services.ocr.image_to_string") as mock_ocr,
    ):
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "   "
        mock_reader.pages = [mock_page]
        mock_reader_class.return_value = mock_reader

        mock_convert.return_value = [MagicMock()]
        mock_ocr.return_value = "Hello from Tesseract"

        result = extract_text_from_pdf_path(mock_pdf_path)

        assert "Hello from Tesseract" in result.text
        assert result.page_count == 1
        mock_convert.assert_called_once()
        mock_ocr.assert_called_once()


def test_extract_text_image_file(mock_image_path):
    """Test image OCR path for PNG/JPG files."""
    with (
        patch("app.services.ocr.shutil.which", return_value="/usr/bin/tesseract"),
        patch("app.services.ocr.Image.open") as mock_open,
        patch("app.services.ocr.image_to_string") as mock_ocr,
    ):
        mock_image_context = MagicMock()
        mock_image_context.__enter__.return_value = MagicMock()
        mock_open.return_value = mock_image_context
        mock_ocr.return_value = "Hello from image OCR"

        result = extract_text_from_file_path(mock_image_path, mime_type="image/png")

        assert "Hello from image OCR" in result.text
        assert result.page_count == 1
        mock_open.assert_called_once_with(mock_image_path)
        mock_ocr.assert_called_once()


def test_ocr_result_bool():
    res_empty = OcrResult("", 0)
    res_text = OcrResult("  hello  ", 1)
    res_whitespace = OcrResult("\n ", 1)

    assert not res_empty
    assert res_text
    assert not res_whitespace
