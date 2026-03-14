import os
import threading
from typing import Optional


MAX_IMAGE_DIMENSION = int(os.getenv("OCR_MAX_IMAGE_DIMENSION", "1400"))

_reader = None
_reader_lock = threading.Lock()


def _get_reader():
    global _reader
    if _reader is not None:
        return _reader

    with _reader_lock:
        if _reader is None:
            import easyocr

            _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_text_from_image(
    file_bytes: bytes,
    timeout_seconds: Optional[int] = None,
) -> str:
    del timeout_seconds  # OCR now runs in-process using a cached reader.

    import cv2
    import numpy as np

    image_np = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Unable to decode image.")

    height, width = image.shape[:2]
    longest_side = max(height, width)
    if longest_side > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / float(longest_side)
        image = cv2.resize(
            image,
            dsize=None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )

    reader = _get_reader()
    results = reader.readtext(image, detail=0, paragraph=False)
    return " ".join(str(text).strip() for text in results if str(text).strip()).strip()
