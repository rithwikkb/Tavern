from urllib.parse import urlparse
import uuid
import requests
from django.conf import settings

def is_fqid(value):
    """
    Check if the value is an FQID (a URL) or a SERIAL (integer).
    """
    try:
        value_str = str(value)
        # Parse the value as a URL
        result = urlparse(value_str)
        return all([result.scheme, result.netloc])  # Valid URL requires scheme and netloc
    except ValueError:
        return False
    
def upload_to_imgur(image_data):
    """
    Upload image to imgur.
    """
    try:
        # endpoint + headers
        url = "https://api.imgur.com/3/image"
        headers = {
            "Authorization": f"Client-ID {settings.IMGUR_CLIENT_ID}",
        }
        files = {
            "image": image_data
        }
        
        # request
        response = requests.post(url, headers=headers, files=files, timeout=15)
        response_data = response.json()
        
        if response.status_code == 200:
            return [response_data["data"]["link"]], None
        else:
            return None, [response_data["data"].get("error", "Unknown error")]
    except Exception as e:
        return None, str(e)
    
def is_valid_uuid(uuid_string):
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False