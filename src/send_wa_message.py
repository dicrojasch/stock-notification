import requests
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self, api_url=None, api_key=None, group_id=None):
        """
        Initializes the WhatsAppClient with API configuration.
        Defaults to environment variables if not provided.
        """
        self.api_url = api_url or os.getenv('WA_API_URL')
        self.api_key = api_key or os.getenv('API_WA_KEY')
        self.group_id = group_id or os.getenv('WHATSAPP_GROUP_ID')

    def _handle_response(self, r):
        """
        Internal helper to handle responses and catch JSON/HTTP errors.
        
        Args:
            r (requests.Response): The response object from requests.
            
        Returns:
            dict: Parsed JSON data or an error dictionary.
        """
        try:
            # Raise an exception for 4xx/5xx status codes
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError:
            logger.error(f"WhatsApp API HTTP Error: {r.status_code} - {r.text}")
            return {"error": f"HTTP {r.status_code}", "status_code": r.status_code, "details": r.text}
        except json.JSONDecodeError:
            logger.error(f"WhatsApp API JSON Decode Error: Expected JSON but got: {r.text[:200]}...")
            return {"error": "Invalid JSON response from server", "status_code": r.status_code, "details": r.text}
        except Exception as e:
            logger.error(f"WhatsApp API Unexpected error: {str(e)}")
            return {"error": str(e), "status_code": getattr(r, 'status_code', None)}

    def send_message(self, phone, message, image_path=None):
        """Sends a text message and optionally an image via file path."""
        headers = {
            "x-api-key": self.api_key
        }
        
        payload = {
            "phone": phone,
            "message": message,
            "imagePath": image_path
        }
        
        try:
            r = requests.post(f"{self.api_url}/send", json=payload, headers=headers)
            return self._handle_response(r)
        except Exception as e:
            logger.error(f"Failed to connect to WhatsApp API: {e}")
            return {"error": "Connection failed", "details": str(e)}

    def send_message_base64(self, phone, message, image_base64):
        """
        Sends a text message along with a base64 encoded image.

        Args:
            phone (str): The recipient's phone number or group ID.
            message (str): The text message content.
            image_base64 (str): The base64 encoded image data.

        Returns:
            dict: API response details.
        """
        if image_base64 is None:
            return self.send_message(phone, message)

        headers = {
            "x-api-key": self.api_key
        }
        
        payload = {
            "phone": phone,
            "message": message,
            "imageBase64": image_base64
        }
        
        try:
            r = requests.post(f"{self.api_url}/send-base64", json=payload, headers=headers)
            return self._handle_response(r)
        except Exception as e:
            logger.error(f"Failed to connect to WhatsApp API: {e}")
            return {"error": "Connection failed", "details": str(e)}

# Usage template for the project:
if __name__ == "__main__":
    # This block is for manual testing of the class
    client = WhatsAppClient()
    
    if not client.api_url or not client.api_key:
        logger.error("WhatsApp API configuration missing in .env")
    else:
        logger.info(f"WhatsApp client initialized with API URL: {client.api_url}")
        # Example usage (uncomment to test if you have a valid base64 string):
        # group_id = client.group_id
        # test_message = "Test message from Stock Notification Bot"
        # result = client.send_message(group_id, test_message)
        # print(result)