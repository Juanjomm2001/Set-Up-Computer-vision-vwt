import os
import time
import logging
import cv2

def capture_image_local(image_dir: str, filename_prefix: str, camera_index: int, retries=3) -> str:
    """
    Captures an image from a local webcam and saves it.
    Retries a few times if the capture fails.
    
    Args:
        image_dir: Directory where images will be stored.
        filename_prefix: Prefix for the saved image filename.
        camera_index: Index of the webcam to use.
        retries: Number of retries if capture fails.
    
    Returns:
        The file path of the saved image, or None if capture fails.
    """
    os.makedirs(image_dir, exist_ok=True)  # Create the image directory if it doesn't exist
    
    for attempt in range(retries):
        cam = cv2.VideoCapture(camera_index)
        ret, frame = cam.read()
        cam.release()
        
        if ret:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.jpg"
            filepath = os.path.join(image_dir, filename)
            cv2.imwrite(filepath, frame)
            logging.info(f"Image saved to: {filepath}")
            return filepath
        else:
            logging.warning(f"Attempt {attempt+1} of {retries} failed to capture image (local webcam).")
            time.sleep(1)
    
    logging.error("Failed to capture image from local webcam after multiple attempts.")
    return None
