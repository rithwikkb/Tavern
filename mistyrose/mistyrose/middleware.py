import re

from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin

class TrailingSlashMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check if the URL doesn't end with a slash and is not an inbox endpoint
        if not request.path.endswith('/') and not request.path.endswith('/inbox'):
            # Collapse leading slashes/backslashes so "//evil.com" can't become a redirect to another site
            path = re.sub(r'^[/\\]+', '/', request.path)
            query = request.META.get('QUERY_STRING', '')
            location = f"{path}/?{query}" if query else f"{path}/"
            # Use 308 to preserve the original HTTP method (POST, PUT, etc.)
            return HttpResponsePermanentRedirect(location, status=308)
        return None
