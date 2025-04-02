import os
import logging
import yaml
from dotenv import load_dotenv

def load_config() -> dict:
    """
    Loads configuration settings from a YAML file for non-sensitive data
    and environment variables for sensitive data.
    
    Returns:
        A dictionary containing all configuration settings.
    """
    try:
        with open("config.yaml", "r") as config_file:
            config = yaml.safe_load(config_file)
    except Exception as e:
        raise Exception(f"Error reading config.yaml: {e}")

    # Load environment variables from .env file (if present)
    load_dotenv()

    # Veolia credentials from environment
    veolia_client_id = os.getenv("VEOLIA_CLIENT_ID")
    veolia_client_secret = os.getenv("VEOLIA_CLIENT_SECRET")
    user_email = os.getenv("USER_EMAIL")
    veolia_api_base_url = os.getenv("VEOLIA_API_BASE_URL")

    # Warn if any Veolia settings are missing
    if not (veolia_client_id and veolia_client_secret and user_email and veolia_api_base_url):
        logging.warning("One or more Veolia configuration variables are missing. Veolia analysis may not work.")

    # Merge into config
    config["VEOLIA_CLIENT_ID"] = veolia_client_id
    config["VEOLIA_CLIENT_SECRET"] = veolia_client_secret
    config["USER_EMAIL"] = user_email
    config["VEOLIA_API_BASE_URL"] = veolia_api_base_url

    return config
