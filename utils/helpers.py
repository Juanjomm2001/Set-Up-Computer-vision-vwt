import logging
import sys
import glob
import os
import time
from logging.handlers import TimedRotatingFileHandler # Import the handler

LOG_DIR = "logs" # Define log directory name
LOG_FILENAME = os.path.join(LOG_DIR, "capture_dataset.log") # Define log file path

def setup_logging():
    """
    Configures logging to output to the console and a rotating file.
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)

    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s" # Added filename/lineno
    )

    # File Handler (Rotates daily, keeps 7 backups)
    file_handler = TimedRotatingFileHandler(
        LOG_FILENAME,
        when="midnight", # Rotate daily at midnight
        interval=1,
        backupCount=7, # Keep logs for 7 days
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Get the root logger and add handlers
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Set root logger level
    # Remove existing basicConfig handlers if any (important for re-config)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info("Logging is set up (Console & Rotating File).")

def cleanup_images(image_dir: str, max_age_seconds: int):
    """
    Deletes images older than max_age_seconds from the image directory.
    
    Args:
        image_dir: Directory where images are stored.
        max_age_seconds: Maximum age in seconds before deletion.
    """
    now = time.time()
    files = glob.glob(os.path.join(image_dir, "*.jpg"))
    for file in files:
        try:
            file_age = now - os.path.getmtime(file)
            if file_age > max_age_seconds:
                os.remove(file)
                logging.info(f"Deleted old image: {file}")
        except Exception as e:
            logging.error(f"Error deleting file {file}: {e}")
