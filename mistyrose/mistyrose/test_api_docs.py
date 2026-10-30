import json

from django.test import TestCase

from .api_docs import ENDPOINTS, TAGS


class ApiDocsTest(TestCase):
    """/swagger/ documents exactly the endpoints in api_docs.ENDPOINTS, each one fully."""

    def setUp(self):
        response = self.client.get('/swagger/?format=openapi')
        self.assertEqual(response.status_code, 200)
        self.schema = json.loads(response.content)
        self.operations = {
            (path, method): operation
            for path, item in self.schema['paths'].items()
            for method, operation in item.items()
            if method != 'parameters'
        }

    def test_every_listed_endpoint_exists_and_nothing_else_is_shown(self):
        # an entry whose URL was renamed or removed would silently drop out of the docs
        self.assertEqual(set(self.operations), set(ENDPOINTS))

    def test_operation_ids_are_unique(self):
        ids = [operation['operationId'] for operation in self.operations.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_operation_is_described(self):
        tags = {name for name, _ in TAGS}
        for key, operation in self.operations.items():
            with self.subTest(endpoint=key):
                self.assertTrue(operation.get('summary'))
                self.assertIn(operation['tags'][0], tags)
                self.assertTrue(operation['responses'])
                for param in self.schema['paths'][key[0]].get('parameters', []):
                    self.assertTrue(param.get('description'), param['name'])

    def test_uses_bearer_tokens_and_marks_public_endpoints(self):
        self.assertEqual(self.schema['info']['title'], 'Tavern API')
        self.assertEqual(list(self.schema['securityDefinitions']), ['Bearer'])
        self.assertEqual(self.operations[('/api/login/', 'post')]['security'], [])
        self.assertNotIn('security', self.operations[('/api/posts/', 'get')])
