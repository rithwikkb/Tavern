"""
Login tokens live in HttpOnly cookies, so JavaScript on the page (including a script
injected through an XSS bug) can't read them.

- The access token cookie is sent with every request to the site.
- The refresh token cookie is only sent to the token refresh and logout URLs.
- API clients (and the Swagger docs) can still send `Authorization: Bearer <token>`.

Because browsers attach cookies to requests automatically, a request authenticated by
cookie must also pass Django's CSRF check before it can change anything.
"""
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication

ACCESS_COOKIE = 'access_token'
REFRESH_COOKIE = 'refresh_token'
# the only URLs that need the refresh token
REFRESH_COOKIE_PATH = '/api/users/'


def enforce_csrf(request):
    """Reject the request unless it carries a valid CSRF token (the same check DRF uses for sessions)."""
    check = CSRFCheck(lambda _request: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')


def set_auth_cookies(response, request, access, refresh):
    lifetimes = settings.SIMPLE_JWT
    common = {
        'httponly': True,
        # in production every request arrives over https (Render forwards the scheme)
        'secure': request.is_secure(),
        'samesite': 'Strict',
    }
    response.set_cookie(ACCESS_COOKIE, str(access), path='/',
                        max_age=int(lifetimes['ACCESS_TOKEN_LIFETIME'].total_seconds()), **common)
    response.set_cookie(REFRESH_COOKIE, str(refresh), path=REFRESH_COOKIE_PATH,
                        max_age=int(lifetimes['REFRESH_TOKEN_LIFETIME'].total_seconds()), **common)


def clear_auth_cookies(response):
    response.delete_cookie(ACCESS_COOKIE, path='/', samesite='Strict')
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite='Strict')


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate with a Bearer header if there is one, otherwise with the access token cookie."""

    def authenticate(self, request):
        if self.get_header(request) is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(ACCESS_COOKIE)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        # cookies are sent automatically, so make sure the request really came from our pages
        enforce_csrf(request)
        return user, validated_token
