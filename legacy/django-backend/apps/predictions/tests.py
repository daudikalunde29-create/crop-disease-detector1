import io
import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image

from apps.accounts.models import User

from .inference import InferenceEngine, NullInferenceEngine, PredictionResult, get_inference_engine

URL = "/api/predict/"
NOT_READY = {
    "status": "not_ready",
    "message": "Prediction service is not available yet. The TensorFlow inference engine will be integrated in a later stage.",
}


def image_bytes(fmt="JPEG", size=(32, 24), color=(30, 140, 60)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()


def upload(data, name="leaf.jpg", content_type="image/jpeg", field="image"):
    return {field: SimpleUploadedFile(name, data, content_type=content_type)}


class StubEngine(InferenceEngine):
    """Stands in for the future TensorFlow engine to prove the boundary is wired. Test-only."""
    seen = []

    def is_ready(self):
        return True

    def predict(self, image):
        StubEngine.seen.append(image.size)
        return PredictionResult(crop="stub-crop", condition="stub-condition", confidence=1.0, model_version="stub-0")


class BrokenEngine(StubEngine):
    def predict(self, image):
        raise RuntimeError("boom")


class PredictTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(email="farmer@example.com", password="Mkulima#2026safe", full_name="F")
        self.c.force_login(self.user)

    # --- access control ---
    def test_unauthenticated_rejected(self):
        r = Client().post(URL, upload(image_bytes()))
        self.assertEqual((r.status_code, r.json()["code"]), (401, "NOT_AUTHENTICATED"))

    def test_get_not_allowed(self):
        self.assertEqual(self.c.get(URL).status_code, 405)

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        r = c.post(URL, upload(image_bytes()))
        self.assertEqual((r.status_code, r.json()["code"]), (403, "CSRF_FAILED"))

    # --- validation ---
    def test_missing_image(self):
        r = self.c.post(URL, {})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "IMAGE_REQUIRED"))

    def test_wrong_field_name(self):
        r = self.c.post(URL, upload(image_bytes(), field="file"))
        self.assertEqual(r.json()["code"], "IMAGE_REQUIRED")

    def test_json_body_rejected(self):
        r = self.c.post(URL, {"image": "x"}, content_type="application/json")
        self.assertEqual((r.status_code, r.json()["code"]), (415, "UNSUPPORTED_MEDIA_TYPE"))

    def test_text_file_pretending_to_be_jpeg(self):
        r = self.c.post(URL, upload(b"this is not an image", "leaf.jpg", "image/jpeg"))
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_IMAGE"))

    def test_html_and_script_payloads_rejected(self):
        for name, data in (("a.png", b"<html><script>alert(1)</script></html>"),
                           ("b.jpg", b"<?php system($_GET['c']); ?>"),
                           ("c.png", b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>")):
            with self.subTest(name):
                r = self.c.post(URL, upload(data, name, "image/png"))
                self.assertEqual(r.status_code, 400)

    def test_empty_file(self):
        r = self.c.post(URL, upload(b""))
        self.assertEqual(r.status_code, 400)
        self.assertIn(r.json()["code"], ("EMPTY_FILE", "IMAGE_REQUIRED"))

    def test_valid_image_format_but_not_allowed_type(self):
        for fmt, name in (("GIF", "x.jpg"), ("BMP", "x.png"), ("TIFF", "x.webp")):
            with self.subTest(fmt):
                r = self.c.post(URL, upload(image_bytes(fmt), name, "image/jpeg"))
                self.assertEqual((r.status_code, r.json()["code"]), (415, "UNSUPPORTED_IMAGE_TYPE"))

    def test_truncated_image_rejected(self):
        data = image_bytes("PNG", size=(200, 200))
        r = self.c.post(URL, upload(data[: len(data) // 2], "leaf.png", "image/png"))
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_IMAGE"))

    @override_settings(PREDICT_MAX_UPLOAD_BYTES=2000)
    def test_oversized_file_rejected(self):
        noisy = os.urandom(64 * 64 * 3)
        buf = io.BytesIO()
        Image.frombytes("RGB", (64, 64), noisy).save(buf, "PNG")
        self.assertGreater(len(buf.getvalue()), 2000)
        r = self.c.post(URL, upload(buf.getvalue(), "big.png", "image/png"))
        self.assertEqual((r.status_code, r.json()["code"]), (413, "FILE_TOO_LARGE"))

    @override_settings(PREDICT_MAX_UPLOAD_BYTES=1000)
    def test_oversized_body_rejected_before_parsing(self):
        r = self.c.post(URL, upload(b"\0" * (200 * 1024), "big.jpg"))
        self.assertEqual((r.status_code, r.json()["code"]), (413, "FILE_TOO_LARGE"))

    @override_settings(PREDICT_MAX_IMAGE_PIXELS=100)
    def test_pixel_dimension_limit(self):
        r = self.c.post(URL, upload(image_bytes("PNG", size=(50, 50)), "p.png", "image/png"))
        self.assertEqual((r.status_code, r.json()["code"]), (413, "IMAGE_DIMENSIONS_TOO_LARGE"))

    # --- accepted images -> honest not_ready ---
    def test_valid_images_accepted_and_report_not_ready(self):
        for fmt, name, ctype in (("JPEG", "a.jpg", "image/jpeg"), ("PNG", "a.png", "image/png"),
                                 ("WEBP", "a.webp", "image/webp")):
            with self.subTest(fmt):
                r = self.c.post(URL, upload(image_bytes(fmt), name, ctype))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json(), NOT_READY)

    def test_validation_is_by_content_not_by_filename_or_declared_type(self):
        r = self.c.post(URL, upload(image_bytes("PNG"), "notes.txt", "application/octet-stream"))
        self.assertEqual(r.json(), NOT_READY)  # real PNG, odd name -> still accepted

    def test_no_fabricated_prediction_in_any_response(self):
        banned = ("disease", "confidence", "treatment", "accuracy", "condition", "crop", "blight", "%")
        responses = [
            self.c.post(URL, upload(image_bytes())),
            self.c.post(URL, {}),
            self.c.post(URL, upload(b"junk")),
        ]
        for r in responses:
            text = r.content.decode().lower()
            for word in banned:
                self.assertNotIn(word, text)
        self.assertEqual(set(responses[0].json()), {"status", "message"})

    def test_upload_is_not_written_to_disk(self):
        before = set(os.listdir(settings.BASE_DIR))
        self.c.post(URL, upload(image_bytes()))
        self.assertEqual(set(os.listdir(settings.BASE_DIR)), before)
        self.assertFalse(hasattr(settings, "MEDIA_ROOT") and os.path.isdir(settings.MEDIA_ROOT or "/nonexistent"))
        self.assertEqual(settings.FILE_UPLOAD_HANDLERS, ["django.core.files.uploadhandler.MemoryFileUploadHandler"])

    # --- the inference boundary ---
    def test_default_engine_is_the_null_engine(self):
        engine = get_inference_engine()
        self.assertIsInstance(engine, NullInferenceEngine)
        self.assertFalse(engine.is_ready())

    @override_settings(PREDICTION_ENGINE="apps.predictions.tests.StubEngine")
    def test_view_hands_a_decoded_image_to_a_ready_engine(self):
        StubEngine.seen.clear()
        r = self.c.post(URL, upload(image_bytes("JPEG", size=(40, 30))))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(StubEngine.seen, [(40, 30)])
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["prediction"]["model_version"], "stub-0")  # whatever the ENGINE returned

    @override_settings(PREDICTION_ENGINE="apps.predictions.tests.BrokenEngine")
    def test_engine_failure_is_a_clean_json_error(self):
        with self.assertLogs("apps.predictions.views", level="ERROR"):
            r = self.c.post(URL, upload(image_bytes()))
        self.assertEqual((r.status_code, r.json()["code"]), (500, "INFERENCE_FAILED"))

    @override_settings(PREDICTION_ENGINE="apps.predictions.tests.StubEngine")
    def test_engine_is_never_called_for_invalid_uploads(self):
        StubEngine.seen.clear()
        self.c.post(URL, upload(b"junk"))
        self.c.post(URL, {})
        self.assertEqual(StubEngine.seen, [])
