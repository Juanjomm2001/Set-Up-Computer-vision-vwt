import time
import json
import random
import base64
import logging
import requests

class VeoliaTokenManager:
    """
    Manages the access token for Veolia Secure GPT API.
    Caches the token and its expiry time to avoid unnecessary requests.
    """
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expiry = 0

    def get_token(self) -> str:
        """
        Obtains a Veolia access token, caching it until near expiry.
        
        Returns:
            The valid access token string or None if the request fails.
        """
        current_time = time.time()
        # Use a buffer of 60 seconds before expiry
        if self.token and (current_time < self.expiry - 60):
            return self.token

        # Token expired or not present, so request a new one
        token_url = "https://api.veolia.com/security/v2/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            response = requests.post(token_url, headers=headers, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                self.expiry = current_time + int(token_data.get("expires_in", 3600))
                logging.info("Obtained new Veolia access token.")
                return self.token
            else:
                logging.error(f"Error obtaining Veolia access token: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logging.error(f"Exception obtaining Veolia access token: {e}")
            return None


def analyze_image_veolia(
    image_path: str,
    prompt: str,
    token_manager: VeoliaTokenManager,
    user_email: str,
    api_base_url: str,
    retries=3
) -> dict:
    """
    Loads an image from disk, converts it to base64, obtains a valid
    access token from Veolia via the token manager, and sends the image
    with the prompt for analysis via the Veolia API.
    
    Args:
        image_path: Path to the saved image.
        prompt: Analysis instructions (including JSON schema).
        token_manager: A VeoliaTokenManager instance.
        user_email: The user's email address.
        api_base_url: The Veolia API endpoint URL.
        retries: Number of retries for the API call.
    
    Returns:
        Parsed JSON result from the Veolia analysis, or None if an error occurs.
    """
    # Read and encode the image in base64
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        logging.error(f"Error reading/encoding image {image_path}: {e}")
        return None

    # Obtain the access token
    access_token = token_manager.get_token()
    if not access_token:
        return None

    # Prepare payload
    payload = {
        "useremail": user_email,
        "history": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "model": "gemini-pro-vision-1.5",
        "temperature": 0.1
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Send API request
    for attempt in range(retries):
        try:
            response = requests.post(api_base_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                response_text = response.text.strip()
                logging.info("Raw Response (Veolia): %s", response_text)
                try:
                    result = json.loads(response_text)
                    logging.info("Parsed JSON response (Veolia): %s", result)
                    return result
                except json.JSONDecodeError:
                    logging.error("Failed to parse JSON response from Veolia.")
                    return None
            else:
                logging.warning(
                    f"Attempt {attempt+1} failed (Veolia): "
                    f"{response.status_code} {response.text}"
                )
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} encountered an exception (Veolia API): {e}")
        time.sleep(2 ** attempt + random.uniform(0, 1))

    logging.error("Failed to analyze image via Veolia API after multiple attempts.")
    return None
