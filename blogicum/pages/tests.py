from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def test_csrf_rejection_renders_custom_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('login'), {})
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'pages/403csrf.html')

    def test_missing_page_renders_custom_page(self):
        response = self.client.get('/missing-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'pages/404.html')

    def test_server_error_renders_custom_page(self):
        client = Client(raise_request_exception=False)
        with patch('blog.views.published_posts', side_effect=RuntimeError):
            response = client.get(reverse('blog:index'))
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'pages/500.html')
