import os
import time
import logging
import random
import string
import requests

def capture_image_reolink(config: dict, filename_prefix: str = "image", retries=3) -> str:
    """
    Captures an image from a Reolink IP camera using its snapshot URL.
    Reads camera credentials from the config and saves the image using
    the same naming convention as the local capture.
    
    Args:
        config: Configuration dictionary that includes a 'camera' section
                with 'ip', 'user', 'password' and an 'image_dir' for saving images.
        filename_prefix: Prefix for the saved image filename.
        retries: Number of retries if capture fails.
    
    Returns:
        The file path of the saved image, or None if capture fails.
    """
    camera_config = config.get("camera", {})
    ip = camera_config.get("ip")
    user = camera_config.get("user")
    password = camera_config.get("password")
    
    if not (ip and user and password):
        logging.error("Reolink camera configuration is incomplete in config.yaml.")
        return None
    
    image_dir = config.get("image_dir", "captured_images")
    os.makedirs(image_dir, exist_ok=True)
    
    # Generate a random string to prevent caching issues (Reolink tip)
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    # Snapshot URL
    snapshot_url = (
        f"http://{ip}/cgi-bin/api.cgi?cmd=Snap&channel=0"
        f"&rs={random_str}&user={user}&password={password}"
    )
    logging.info(f"Fetching Reolink snapshot from: {snapshot_url}")
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.jpg"
    filepath = os.path.join(image_dir, filename)
    
    for attempt in range(retries):
        try:
            response = requests.get(snapshot_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.info(f"Reolink snapshot saved to: {filepath}")
                return filepath
            else:
                logging.warning(f"Attempt {attempt+1} failed (Reolink): status code {response.status_code}")
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} encountered exception (Reolink): {e}")
        time.sleep(1)
    
    error_msg = "Failed to capture image from Reolink camera after multiple attempts."
    logging.error(error_msg)
    return None
