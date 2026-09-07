import io
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch

from services.ocr_service import OCRService, ocr_service


class TestOCRServiceUnit:
    """Unit tests for OCRService in-memory image processing and error resilience."""

    def test_extract_text_with_mock_engine(self):
        service = OCRService()

        # Mock engine output matching PaddleOCR's format:
        # [ [ [box_coords, ("Extracted Text Line 1", 0.99)], [box_coords, ("Second Line", 0.95)] ] ]
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("Software Developer", 0.99)],
                [[[0, 15], [10, 15], [10, 25], [0, 25]], ("Python and Docker", 0.97)],
            ]
        ]
        service._ocr_engine = mock_engine

        # Test with PIL Image
        img = Image.new("RGB", (100, 100), color="white")
        result = service.extract_text_from_image(img)
        assert "Software Developer" in result
        assert "Python and Docker" in result
        assert "\n" in result

    def test_extract_text_from_image_bytes(self):
        service = OCRService()
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("Recognized from bytes", 0.98)]
            ]
        ]
        service._ocr_engine = mock_engine

        # Create valid PNG bytes in-memory
        bio = io.BytesIO()
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(bio, format="PNG")
        png_bytes = bio.getvalue()

        result = service.extract_text_from_image(png_bytes)
        assert result == "Recognized from bytes"

    def test_extract_text_from_numpy_array(self):
        service = OCRService()
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("Recognized from numpy", 0.95)]
            ]
        ]
        service._ocr_engine = mock_engine

        arr = np.zeros((50, 50, 3), dtype=np.uint8)
        result = service.extract_text_from_image(arr)
        assert result == "Recognized from numpy"

    def test_extract_text_empty_engine_result(self):
        service = OCRService()
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = []
        service._ocr_engine = mock_engine

        img = Image.new("RGB", (50, 50), color="white")
        result = service.extract_text_from_image(img)
        assert result == ""

    def test_extract_text_engine_exception_safe(self):
        service = OCRService()
        mock_engine = MagicMock()
        mock_engine.ocr.side_effect = RuntimeError("PaddleOCR CUDA/Memory failure")
        service._ocr_engine = mock_engine

        # Engine failure must NOT raise an unhandled exception or crash the server
        img = Image.new("RGB", (50, 50), color="white")
        result = service.extract_text_from_image(img)
        assert result == ""

    def test_extract_text_unsupported_input_type(self):
        service = OCRService()
        # Passing an invalid type (e.g. integer) should return empty string safely
        result = service.extract_text_from_image(12345)
        assert result == ""

