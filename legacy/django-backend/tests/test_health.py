from django.test import TestCase


class HealthTests(TestCase):
    def test_health_ok(self):
        r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_unknown_endpoint_json_404(self):
        r = self.client.get("/api/does-not-exist/")
        self.assertEqual(r.status_code, 404)
