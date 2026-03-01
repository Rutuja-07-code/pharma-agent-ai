import easyocr
import cv2
import numpy as np

# Load model once (important for performance)
reader = easyocr.Reader(['en'])

def extract_text_from_image(file_bytes):
    # Convert bytes to numpy array
    image_np = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    results = reader.readtext(image)

    extracted_text = " ".join([text for (_, text, _) in results])

    return extracted_text