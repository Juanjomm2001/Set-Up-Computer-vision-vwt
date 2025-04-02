import time
import logging
import signal
import sys
import os
from config.settings import load_config
from utils.helpers import setup_logging
from camera.local_camera import capture_image_local
from camera.reolink_camera import capture_image_reolink
from utils.drive_uploader import upload_file  # Your custom uploader with supportsAllDrives=True

def signal_handler(sig, frame):
    """
    Graceful shutdown handler for Ctrl+C or SIGTERM.
    """
    logging.info("Shutdown signal received. Exiting gracefully...")
    sys.exit(0)

def main():
    setup_logging()
    config = load_config()

    # 1. Capture and duration settings
    capture_interval = config.get("dataset_capture_interval", 60)
    max_duration_seconds = config.get("max_duration_seconds", None)
    dataset_dir = config.get("dataset_dir", "dataset_images")

    # 2. Camera settings
    camera_config = config.get("camera", {})
    cam_type = camera_config.get("type", "local").lower()
    camera_index = config.get("camera_index", 0)

    # 3. Google Drive settings
    google_drive_config = config.get("google_drive", {})
    drive_enabled = google_drive_config.get("enabled", False)
    service_account_file = google_drive_config.get("service_account_file", "credentials/katodiskbeskyttelseServiceAccount.json")

    # The folder ID is stored in your .env as GOOGLE_DRIVE_FOLDER_ID
    drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", None)

    # 4. Prepare for timed run
    start_time = time.time()
    MAX_CONSECUTIVE_FAILURES = 10 # Hardcoded threshold
    consecutive_failures = 0 # Initialize failure counter
    logging.info(f"Starting dataset capture loop (interval={capture_interval}s, max_duration={max_duration_seconds or '∞'}s, max_consecutive_failures={MAX_CONSECUTIVE_FAILURES}).")

    while True:
        loop_start = time.time()
        # 4a. If we have a max duration, check if we've hit the limit
        if max_duration_seconds is not None:
            elapsed = time.time() - start_time
            if elapsed >= max_duration_seconds:
                logging.info("Maximum capture duration reached. Exiting loop.")
                break
        
        try:
            # 5. Create daily subfolder (e.g., dataset_images/20250321)
            today = time.strftime("%Y%m%d")
            daily_dir = os.path.join(dataset_dir, today)
            os.makedirs(daily_dir, exist_ok=True)

            # 6. Capture image
            if cam_type == "reolink":
                temp_config = dict(config)
                temp_config["image_dir"] = daily_dir  # override for the reolink capture
                # Add retry logic within capture functions if needed,
                # but here we handle the case where it returns None after retries.
                image_path = capture_image_reolink(temp_config, filename_prefix="dataset_image")
                if image_path is None:
                    consecutive_failures += 1
                    logging.error(f"Failed to capture image from Reolink (Attempt {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}).")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logging.critical(f"Reached maximum consecutive capture failures ({MAX_CONSECUTIVE_FAILURES}). Exiting.")
                        sys.exit(1)
                    time.sleep(10) # Pause before next attempt
                    continue # Skip rest of loop iteration
                else:
                    consecutive_failures = 0 # Reset counter on success
            else: # local camera
                image_path = capture_image_local(daily_dir, "dataset_image", camera_index)
                if image_path is None:
                    consecutive_failures += 1
                    logging.error(f"Failed to capture image from local webcam (Attempt {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}).")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logging.critical(f"Reached maximum consecutive capture failures ({MAX_CONSECUTIVE_FAILURES}). Exiting.")
                        sys.exit(1)
                    time.sleep(10) # Pause before next attempt
                    continue # Skip rest of loop iteration
                else:
                    consecutive_failures = 0 # Reset counter on success
            
            # If we reach here, capture was successful (failure would have 'continue'd)
            logging.info(f"Image captured successfully: {image_path}")

            # 7. (Optional) Upload to Google Drive
            if drive_enabled:
                if not drive_folder_id:
                    logging.error("GOOGLE_DRIVE_FOLDER_ID is not set. Cannot upload.")
                else:
                    # Wrap upload in its own try/except to handle upload failures
                    try:
                        file_id = upload_file(
                            file_path=image_path,
                            folder_id=drive_folder_id,
                            service_account_file=service_account_file
                        )
                        if file_id:
                            logging.info(f"Uploaded to Drive with file ID: {file_id}")
                        else:
                            # upload_file should ideally raise an exception on failure,
                            # but if it returns None/False, log it.
                            logging.error("Upload to Google Drive failed (returned non-ID).")
                    except Exception as upload_exc:
                        logging.exception("Error during Google Drive upload: %s", upload_exc)
                        # Continue loop even if upload fails
            
        except Exception as e:
            # Catch ANY other unexpected error in the loop
            logging.exception("Unexpected error in capture loop iteration: %s", e)
            # Don't exit, just log, wait a bit, and continue
            time.sleep(10) # Pause before next attempt
            continue # Skip to next iteration
        
        # 8. Sleep until next capture interval
        loop_end = time.time()
        elapsed = loop_end - loop_start
        remaining = capture_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        
        # 9. Log the time taken for the loop iteration
        logging.info(f"Loop iteration took {elapsed:.2f} seconds. Remaining time: {remaining:.2f} seconds.")
    logging.info("Capture dataset process completed successfully.")

if __name__ == "__main__":
    # 9. Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
