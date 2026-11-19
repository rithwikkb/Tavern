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
