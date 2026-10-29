from urllib.parse import urlparse
import uuid
import requests
from django.conf import settings

def get_request_author(request):
    """
    Return the Author profile of the logged-in user, or None.
    """
    from users.models import Author

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    return Author.objects.filter(user=user).first()

def is_request_author(request, *author_ids):
    """
    Check whether the logged-in user is one of the given authors.
    """
    author = get_request_author(request)
    if author is None:
        return False
    return str(author.id) in {str(author_id) for author_id in author_ids}

def are_friends(author_a, author_b):
    """
    Two authors are friends when each follows the other.
    """
    from users.models import Follows

    return (
        Follows.objects.filter(local_follower_id=author_a, followed_id=author_b, status='ACCEPTED').exists()
        and Follows.objects.filter(local_follower_id=author_b, followed_id=author_a, status='ACCEPTED').exists()
    )

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