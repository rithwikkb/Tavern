import json

from django.test import Client, TestCase, override_settings


class HealthCheckTest(TestCase):
    def test_reports_ok_without_touching_the_database(self):
        # monitoring it every few minutes mustn't keep the free Postgres database awake
        with self.assertNumQueries(0):
            response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'status': 'ok'})
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_only_answers_get(self):
        self.assertEqual(self.client.post('/healthz/').status_code, 405)


class HttpsTest(TestCase):
    """In production every request is redirected to https, and browsers are told to stay there."""

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_plain_http_is_redirected_to_https(self):
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response['Location'].startswith('https://'))

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_check_answers_over_http_too(self):
        self.assertEqual(self.client.get('/healthz/').status_code, 200)

    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_hsts_header_on_https_responses(self):
        response = self.client.get('/healthz/', secure=True)
        self.assertEqual(response['Strict-Transport-Security'], 'max-age=3600; includeSubDomains')


class CsrfTest(TestCase):
    """CSRF protection covers cookie-based pages without getting in the way of the JWT API."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_api_works_without_a_csrf_token(self):
        response = self.client.post('/api/login/', {'username': 'nobody', 'password': 'wrong'},
                                    content_type='application/json')
        # rejected for the wrong password, not for a missing CSRF token
        self.assertEqual(response.status_code, 401)

    def test_admin_login_requires_a_csrf_token(self):
        response = self.client.post('/admin/login/', {'username': 'x', 'password': 'y'})
        self.assertEqual(response.status_code, 403)


class ErrorDetailsStayOnServerTest(TestCase):
    """Unexpected errors are logged in full but only a generic message reaches the client."""
    SECRET = 'relation "users_author" does not exist at /srv/app/db.py'

    def assert_hidden(self, response):
        self.assertNotIn(self.SECRET, response.content.decode())

    def test_signup_failure(self):
        from unittest.mock import patch
        with patch('users.views.create_author', side_effect=Exception(self.SECRET)), \
                self.assertLogs('users.views', level='ERROR'):
            response = self.client.post('/api/signup/', {
                'username': 'leaky', 'email': 'leaky@example.com', 'password': 'a-long-passphrase-9',
                'displayName': 'Leaky'}, content_type='application/json')
        self.assertEqual(response.status_code, 500)
        self.assert_hidden(response)

    def test_image_upload_failure(self):
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        image = SimpleUploadedFile('me.png', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        with patch('users.views.upload_to_imgur', return_value=(None, self.SECRET)), \
                self.assertLogs('users.views', level='ERROR'):
            response = self.client.post('/authors/leaky/upload_image/', {'profile_image': image})
        self.assertEqual(response.status_code, 502)
        self.assert_hidden(response)

    def test_post_image_failure(self):
        from unittest.mock import patch
        from django.contrib.auth.models import User
        from posts.models import Post
        from users.models import Author
        user = User.objects.create_user(username='painter', password='somethingHardToCrack357')
        author = Author.objects.create(user=user, display_name='Painter', host='http://testserver')
        post = Post.objects.create(author_id=author, title='pic', content='aGVsbG8=',
                                   content_type='image/png;base64', visibility='PUBLIC')
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(user).access_token
        # fail while building the image response (patching base64 would also break JWT login)
        with patch('posts.views.FileResponse', side_effect=ValueError(self.SECRET)), \
                self.assertLogs('posts.views', level='ERROR'):
            response = self.client.get(f'/api/authors/{author.id}/posts/{post.id}/image/',
                                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 500)
        self.assert_hidden(response)
