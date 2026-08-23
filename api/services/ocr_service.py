import io
import logging
from typing import Union, List
import numpy as np
from PIL import Image

logger = logging.getLogger("api.services.ocr")

class OCRService:
    """
    In-memory OCR engine powered by PaddleOCR (Apache 2.0).
    Processes PIL Images, Numpy arrays, or image bytes completely in RAM without disk I/O.
    Lazy-loads PaddleOCR model on first invocation to maintain fast server startup.
    """

    def __init__(self):
        self._ocr_engine = None

    def _get_engine(self):
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
                logger.info("Initializing in-memory PaddleOCR engine...")
                # Initialize PaddleOCR with English language and angle classification
                self._ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")
                logger.info("PaddleOCR engine initialized successfully.")
            except Exception as exc:
                logger.error("Failed to initialize PaddleOCR engine: %s", exc, exc_info=True)
                raise
        return self._ocr_engine

    def extract_text_from_image(self, image_input: Union[bytes, Image.Image, np.ndarray]) -> str:
        """
        Run in-memory OCR on image input and return extracted text string.
        Catches any engine-level exceptions safely to prevent server crashes.
        """
        try:
            # 1. Convert input to numpy array in RGB format
            if isinstance(image_input, bytes):
                pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
                img_arr = np.array(pil_img)
            elif isinstance(image_input, Image.Image):
                pil_img = image_input.convert("RGB")
                img_arr = np.array(pil_img)
            elif isinstance(image_input, np.ndarray):
                img_arr = image_input
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")

            # 2. Run PaddleOCR
            engine = self._get_engine()
            result = engine.ocr(img_arr)

            if not result or not result[0]:
                return ""

            # 3. Format recognized text lines
            extracted_lines: List[str] = []
            for line in result[0]:
                if line and len(line) >= 2 and line[1] and len(line[1]) >= 1:
                    text = line[1][0]
                    if text and text.strip():
                        extracted_lines.append(text.strip())

            return "\n".join(extracted_lines)
        except Exception as exc:
            logger.error("In-memory OCR processing failed: %s", exc, exc_info=True)
            return ""

ocr_service = OCRService()
