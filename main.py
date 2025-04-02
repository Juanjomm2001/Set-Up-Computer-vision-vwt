import time
import logging
import signal
import sys
import json

from config.settings import load_config
from utils.helpers import setup_logging, cleanup_images
from analysis.veolia_analysis import analyze_image_veolia, VeoliaTokenManager
from camera.local_camera import capture_image_local
from camera.reolink_camera import capture_image_reolink


def signal_handler(sig, frame):
    """
    Handles signals (e.g., SIGINT, SIGTERM) for graceful shutdown.
    """
    logging.info("Received shutdown signal. Exiting gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main_loop(config: dict):
    """
    Main loop that continuously captures images, analyzes them (using Veolia API),
    and cleans up old images.
    
    Args:
        config: Configuration dictionary loaded from YAML + environment.
    """
    prompt = config.get("prompt")
    if not prompt:
        logging.error("No 'prompt' provided in configuration.")
        return

    cam_type = config.get("camera", {}).get("type", "local").lower()
    camera_index = config.get("camera_index", 0)
    image_dir = config.get("image_dir", "captured_images")
    capture_interval = config.get("capture_interval", 10)
    cleanup_age = config.get("cleanup_age", 300)

    # Prepare Veolia token manager
    veolia_client_id = config.get("VEOLIA_CLIENT_ID")
    veolia_client_secret = config.get("VEOLIA_CLIENT_SECRET")
    user_email = config.get("USER_EMAIL")
    api_base_url = config.get("VEOLIA_API_BASE_URL")

    if not (veolia_client_id and veolia_client_secret and user_email and api_base_url):
        logging.error("Missing Veolia configuration. Exiting.")
        return
    token_manager = VeoliaTokenManager(veolia_client_id, veolia_client_secret)

    logging.info("Starting main loop for water detection...")

    while True:
        # 1. Capture Image
        if cam_type == "reolink":
            image_path = capture_image_reolink(config)
        else:
            image_path = capture_image_local(image_dir, "image", camera_index)

        if image_path is None:
            logging.warning("Failed to capture image. Skipping analysis.")
            sys.exit(1)

        # 2. Analyze via Veolia
        else:
            result = analyze_image_veolia(
                image_path=image_path,
                prompt=prompt,
                token_manager=token_manager,
                user_email=user_email,
                api_base_url=api_base_url
            )

            # 3. Check for water presence
            if result:
                # Example of the desired JSON structure:
                # {
                #   "water_detected": true/false,
                #   "confidence": 89,
                #   "analysis_reason": "Explanation text..."
                # }
                if isinstance(result, str): # Handle the case where the API returns a string directly (not JSON)
                    result = json.loads(result)
                if result.get("water_detected", False):
                    logging.info("ALERT: Water detected on the floor!")
                else:
                    logging.info("No water detected on the floor.")

            else:
                logging.info("Analysis returned no result (Veolia API may have failed).")

        # 4. Cleanup old images
        cleanup_images(image_dir, cleanup_age)

        # 5. Sleep until next capture
        time.sleep(capture_interval)

if __name__ == "__main__":
    setup_logging()
    config = load_config()
    main_loop(config)
