from django.test import Client, TestCase

from .models import User

VALID = {"fullName": "John Doe", "email": "john@example.com", "phone": "+255700000000",
         "password": "Mkulima#2026safe"}


class AuthTests(TestCase):
    def setUp(self):
        self.c = Client()

    def post(self, url, body):
        return self.c.post(url, body, content_type="application/json")

    def register(self, **over):
        return self.post("/api/auth/register/", {**VALID, **over})

    # Registration
    def test_register_valid_creates_session(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        u = r.json()["user"]
        self.assertEqual(set(u), {"id", "name", "email", "phone", "role", "provider", "createdAt"})
        self.assertEqual((u["role"], u["provider"]), ("farmer", "email"))
        self.assertTrue(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_register_duplicate_email(self):
        self.register()
        r = Client().post("/api/auth/register/", {**VALID, "email": "JOHN@example.com"},
                          content_type="application/json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["code"], "EMAIL_EXISTS")

    def test_register_invalid_email(self):
        r = self.register(email="not-an-email")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["fields"])

    def test_register_missing_fields(self):
        r = self.post("/api/auth/register/", {"email": "a@b.com"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("fullName", r.json()["fields"])
        self.assertIn("password", r.json()["fields"])

    def test_register_weak_password(self):
        for pw in ("123", "password", "12345678901"):
            r = self.register(password=pw)
            self.assertEqual(r.status_code, 400, pw)
            self.assertIn("password", r.json()["fields"])

    # Login
    def make_user(self):
        return User.objects.create_user(email="john@example.com", password=VALID["password"], full_name="John")

    def test_login_correct(self):
        self.make_user()
        r = self.post("/api/auth/login/", {"email": "john@example.com", "password": VALID["password"], "remember": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["email"], "john@example.com")
        self.assertIn("sessionid", r.cookies)

    def test_login_wrong_password(self):
        self.make_user()
        r = self.post("/api/auth/login/", {"email": "john@example.com", "password": "wrong-pass-1"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"code": "AUTH_ERROR", "message": "Invalid email or password."})

    def test_login_unknown_email(self):
        r = self.post("/api/auth/login/", {"email": "nobody@example.com", "password": "whatever123"})
        self.assertEqual(r.json()["code"], "AUTH_ERROR")

    def test_login_without_remember_is_browser_session(self):
        self.make_user()
        self.post("/api/auth/login/", {"email": "john@example.com", "password": VALID["password"], "remember": False})
        self.assertTrue(self.c.session.get_expire_at_browser_close())

    # Session / logout / me
    def test_session_unauthenticated(self):
        r = self.c.get("/api/auth/session/")
        self.assertEqual(r.json(), {"authenticated": False})
        self.assertIn("csrftoken", r.cookies)

    def test_logout_destroys_session(self):
        self.register()
        self.assertEqual(self.post("/api/auth/logout/", {}).status_code, 200)
        self.assertEqual(self.c.get("/api/auth/session/").json(), {"authenticated": False})
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 401)

    def test_me(self):
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.c.get("/api/auth/me/").json()["code"], "NOT_AUTHENTICATED")
        self.register()
        self.assertEqual(self.c.get("/api/auth/me/").json()["user"]["email"], VALID["email"])

    # Security
    def test_password_hashed_and_never_returned(self):
        r = self.register()
        user = User.objects.get(email=VALID["email"])
        self.assertNotEqual(user.password, VALID["password"])
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertNotIn(VALID["password"], r.content.decode())
        self.assertNotIn("password", r.json()["user"])

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post("/api/auth/register/", VALID, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "CSRF_FAILED")
        token = c.get("/api/auth/session/").cookies["csrftoken"].value
        r = c.post("/api/auth/register/", VALID, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 201)

    def test_invalid_json(self):
        r = self.c.post("/api/auth/login/", "{bad", content_type="application/json")
        self.assertEqual(r.json()["code"], "INVALID_JSON")


# =============================================================================
# M4.2 tests
# =============================================================================
import re
import time
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from google.auth import crypt as google_crypt
from google.auth import jwt as google_jwt

from .google import GoogleNotConfigured, GoogleTokenError, GoogleUnavailable, verify_google_id_token

CLIENT_ID = "test-client-123.apps.googleusercontent.com"
GOOGLE_CLAIMS = {"sub": "google-sub-1", "email": "farmer@example.com", "name": "Asha Farmer",
                 "picture": "https://example.com/a.png"}
OLD_PW = "Mkulima#2026safe"
NEW_PW = "Shamba!Mpya2027"


class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.c = Client()

    def post(self, url, body=None, client=None):
        return (client or self.c).post(url, body if body is not None else {}, content_type="application/json")

    def make_user(self, email="john@example.com", password=OLD_PW, **extra):
        return User.objects.create_user(email=email, password=password, full_name=extra.pop("full_name", "John"), **extra)


# --- Google: the real verification layer, offline, with a locally signed JWT ---

class GoogleVerificationLayerTests(TestCase):
    """Runs google-auth's REAL signature/audience/issuer/expiry checks against a token
    signed with a throw-away key; only the download of Google's public keys is replaced."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption()).decode()
        cls.pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        cls.signer = google_crypt.RSASigner.from_string(priv, "k1")

    def token(self, **over):
        now = int(time.time())
        claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "g-1", "email": "Farmer@Example.com",
                  "email_verified": True, "name": "Asha", "iat": now, "exp": now + 600}
        claims.update(over)
        tok = google_jwt.encode(self.signer, claims, {"kid": "k1"})
        return tok.decode() if isinstance(tok, bytes) else tok

    def verify(self, tok):
        with mock.patch("google.oauth2.id_token._fetch_certs", return_value={"k1": self.pub}):
            return verify_google_id_token(tok)

    @override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
    def test_valid_token_returns_normalised_claims(self):
        c = self.verify(self.token())
        self.assertEqual((c["sub"], c["email"], c["name"]), ("g-1", "farmer@example.com", "Asha"))

    @override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
    def test_rejects_bad_tokens(self):
        now = int(time.time())
        cases = {
            "malformed": "not-a-jwt",
            "expired": self.token(iat=now - 4000, exp=now - 3600),
            "wrong audience": self.token(aud="someone-else.apps.googleusercontent.com"),
            "wrong issuer": self.token(iss="https://evil.example.com"),
            "no sub": self.token(sub=""),
            "no email": self.token(email=""),
        }
        for name, tok in cases.items():
            with self.subTest(name), self.assertRaises(GoogleTokenError):
                self.verify(tok)

    @override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
    def test_rejects_unverified_email(self):
        with self.assertRaises(GoogleTokenError) as ctx:
            self.verify(self.token(email_verified=False))
        self.assertEqual(ctx.exception.reason, "email_unverified")

    @override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
    def test_rejects_token_signed_with_a_different_key(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_pem = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()).decode()
        now = int(time.time())
        forged = google_jwt.encode(google_crypt.RSASigner.from_string(other_pem, "k1"),
                                   {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": "x",
                                    "email": "a@b.com", "email_verified": True, "iat": now, "exp": now + 600},
                                   {"kid": "k1"})
        forged = forged.decode() if isinstance(forged, bytes) else forged
        with self.assertRaises(GoogleTokenError):
            self.verify(forged)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_not_configured(self):
        with self.assertRaises(GoogleNotConfigured):
            verify_google_id_token("anything")

    @override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
    def test_google_unreachable(self):
        from google.auth.exceptions import TransportError
        with mock.patch("google.oauth2.id_token._fetch_certs", side_effect=TransportError("down")):
            with self.assertRaises(GoogleUnavailable):
                verify_google_id_token("a.b.c")


# --- Google: the endpoint, with the verification layer mocked ---

@override_settings(GOOGLE_CLIENT_ID=CLIENT_ID)
class GoogleEndpointTests(ApiTestCase):
    URL = "/api/auth/google/"

    def google(self, claims=None, **over):
        claims = {**GOOGLE_CLAIMS, **(claims or {}), **over}
        with mock.patch("apps.accounts.views.verify_google_id_token", return_value=claims) as m:
            r = self.post(self.URL, {"credential": "fake.google.token"})
        self.assertEqual(m.call_count, 1)
        return r

    def test_missing_credential(self):
        r = self.post(self.URL, {})
        self.assertEqual(r.status_code, 400)
        self.assertIn("credential", r.json()["fields"])

    def test_blank_credential(self):
        self.assertEqual(self.post(self.URL, {"credential": "   "}).status_code, 400)

    def test_malformed_credential_rejected(self):
        # Real verification path; only the key download is stubbed.
        with mock.patch("google.oauth2.id_token._fetch_certs", return_value={}):
            r = self.post(self.URL, {"credential": "garbage"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "INVALID_GOOGLE_TOKEN")
        self.assertFalse(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_invalid_token_rejected_and_no_session(self):
        with mock.patch("apps.accounts.views.verify_google_id_token", side_effect=GoogleTokenError("invalid")):
            r = self.post(self.URL, {"credential": "x.y.z"})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_GOOGLE_TOKEN"))
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_unverified_email_rejected(self):
        with mock.patch("apps.accounts.views.verify_google_id_token", side_effect=GoogleTokenError("email_unverified")):
            r = self.post(self.URL, {"credential": "x.y.z"})
        self.assertEqual(r.json()["code"], "GOOGLE_EMAIL_UNVERIFIED")
        self.assertEqual(User.objects.count(), 0)

    def test_not_configured_is_503(self):
        with mock.patch("apps.accounts.views.verify_google_id_token", side_effect=GoogleNotConfigured()):
            r = self.post(self.URL, {"credential": "x.y.z"})
        self.assertEqual((r.status_code, r.json()["code"]), (503, "GOOGLE_NOT_CONFIGURED"))

    def test_google_unreachable_is_503(self):
        with mock.patch("apps.accounts.views.verify_google_id_token", side_effect=GoogleUnavailable()):
            r = self.post(self.URL, {"credential": "x.y.z"})
        self.assertEqual((r.status_code, r.json()["code"]), (503, "GOOGLE_UNAVAILABLE"))

    def test_new_google_user_created_with_session(self):
        r = self.google()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["created"])
        self.assertFalse(body["linked"])
        u = body["user"]
        self.assertEqual(set(u), {"id", "name", "email", "phone", "role", "provider", "createdAt"})
        self.assertEqual((u["name"], u["email"], u["provider"], u["role"]), ("Asha Farmer", "farmer@example.com", "google", "farmer"))
        user = User.objects.get(email="farmer@example.com")
        self.assertEqual(user.google_sub, "google-sub-1")
        self.assertEqual(user.picture_url, "https://example.com/a.png")
        self.assertFalse(user.has_usable_password())
        self.assertIn("sessionid", r.cookies)
        s = self.c.get("/api/auth/session/").json()
        self.assertTrue(s["authenticated"])
        self.assertEqual(s["user"]["email"], "farmer@example.com")
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 200)

    def test_google_token_is_not_the_session(self):
        r = self.google()
        self.assertNotIn("fake.google.token", r.content.decode())
        self.assertNotIn("fake.google.token", str(dict(r.cookies)))

    def test_returning_google_user_is_not_duplicated(self):
        self.google()
        r = self.google()
        self.assertFalse(r.json()["created"])
        self.assertEqual(User.objects.count(), 1)

    def test_returning_user_matched_by_sub_even_if_email_changed(self):
        self.google()
        r = self.google(email="renamed@example.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(r.json()["user"]["email"], "farmer@example.com")

    def test_existing_email_account_is_linked_not_duplicated(self):
        existing = self.make_user(email="farmer@example.com", full_name="Asha Local", phone="+255700000001")
        r = self.google()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["linked"])
        self.assertFalse(r.json()["created"])
        self.assertEqual(User.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, "google-sub-1")
        self.assertEqual(existing.provider, "google")
        self.assertEqual((existing.full_name, existing.phone), ("Asha Local", "+255700000001"))  # profile kept

    def test_linking_discards_old_local_password(self):
        """Pre-hijack defence: the unverified local password must not survive linking."""
        self.make_user(email="farmer@example.com")
        self.google()
        self.assertFalse(User.objects.get(email="farmer@example.com").has_usable_password())
        r = self.post("/api/auth/login/", {"email": "farmer@example.com", "password": OLD_PW}, client=Client())
        self.assertEqual(r.status_code, 400)

    def test_linking_invalidates_pre_existing_sessions(self):
        attacker = Client()
        self.post("/api/auth/register/", {**VALID, "email": "farmer@example.com"}, client=attacker)
        self.assertTrue(attacker.get("/api/auth/session/").json()["authenticated"])
        self.google()  # the real owner signs in with Google
        self.assertFalse(attacker.get("/api/auth/session/").json()["authenticated"])

    def test_email_matching_is_case_insensitive(self):
        self.make_user(email="farmer@example.com")
        self.google(email="Farmer@Example.com")
        self.assertEqual(User.objects.count(), 1)

    def test_email_linked_to_different_google_account_conflicts(self):
        self.google()
        r = self.google(sub="a-different-google-sub")
        self.assertEqual((r.status_code, r.json()["code"]), (409, "GOOGLE_ACCOUNT_CONFLICT"))
        self.assertEqual(User.objects.count(), 1)

    def test_disabled_account_cannot_sign_in(self):
        self.make_user(email="farmer@example.com", is_active=False)
        r = self.google()
        self.assertEqual((r.status_code, r.json()["code"]), (403, "ACCOUNT_DISABLED"))
        self.assertFalse(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_name_falls_back_to_email_local_part(self):
        self.google(name="")
        self.assertEqual(User.objects.get().full_name, "farmer")

    def test_google_user_cannot_password_login(self):
        self.google()
        r = self.post("/api/auth/login/", {"email": "farmer@example.com", "password": "anything12345"}, client=Client())
        self.assertEqual(r.json()["code"], "AUTH_ERROR")

    def test_logout_after_google_login(self):
        self.google()
        self.post("/api/auth/logout/")
        self.assertFalse(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_csrf_enforced_on_google_endpoint(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(self.URL, {"credential": "x.y.z"}, content_type="application/json")
        self.assertEqual((r.status_code, r.json()["code"]), (403, "CSRF_FAILED"))

    def test_config_endpoint_exposes_only_client_id(self):
        r = self.c.get("/api/auth/google/config/")
        self.assertEqual(r.json(), {"enabled": True, "clientId": CLIENT_ID})

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_config_endpoint_when_unconfigured(self):
        self.assertEqual(self.c.get("/api/auth/google/config/").json(), {"enabled": False, "clientId": ""})


# --- Password reset ---

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_ORIGIN="http://localhost:8080")
class PasswordResetTests(ApiTestCase):
    REQ, CONFIRM = "/api/auth/password-reset/", "/api/auth/password-reset-confirm/"

    def token_from_mail(self):
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        m = re.search(r"reset-password\.html\?token=([\w\-.]+)", msg.body)
        self.assertIsNotNone(m, msg.body)
        return m.group(1)

    def test_request_sends_email_with_link_and_generic_response(self):
        self.make_user()
        r = self.post(self.REQ, {"email": "john@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "If an account exists for this email, password reset instructions have been sent.")
        self.assertEqual(mail.outbox[0].to, ["john@example.com"])
        self.assertIn("http://localhost:8080/site/pages/reset-password.html?token=", mail.outbox[0].body)
        self.assertNotIn(OLD_PW, mail.outbox[0].body)

    def test_unknown_email_gets_identical_response_and_sends_nothing(self):
        self.make_user()
        known = self.post(self.REQ, {"email": "john@example.com"})
        mail.outbox.clear()
        unknown = self.post(self.REQ, {"email": "nobody@example.com"})
        self.assertEqual((unknown.status_code, unknown.json()), (known.status_code, known.json()))
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_format_is_a_validation_error(self):
        self.assertEqual(self.post(self.REQ, {"email": "nope"}).status_code, 400)
        self.assertEqual(self.post(self.REQ, {}).status_code, 400)

    def test_inactive_user_gets_no_email(self):
        self.make_user(is_active=False)
        self.post(self.REQ, {"email": "john@example.com"})
        self.assertEqual(len(mail.outbox), 0)

    def test_email_lookup_is_case_insensitive(self):
        self.make_user()
        self.post(self.REQ, {"email": "JOHN@Example.com"})
        self.assertEqual(len(mail.outbox), 1)

    def test_tokens_are_not_stored_in_the_database(self):
        user = self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail().partition(".")[2]
        from django.db import connection
        with connection.cursor() as cur:
            for (table,) in [(t,) for t in connection.introspection.table_names()]:
                cur.execute(f'SELECT * FROM "{table}"')
                self.assertNotIn(token, str(cur.fetchall()), table)
        user.refresh_from_db()
        self.assertNotIn(token, user.password)

    def test_full_reset_flow_changes_password(self):
        self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail()
        r = self.post(self.CONFIRM, {"token": token, "password": NEW_PW})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["success"])
        self.assertNotIn(NEW_PW, r.content.decode())
        user = User.objects.get(email="john@example.com")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(NEW_PW))
        # old password dead, new password works through the real login endpoint
        self.assertEqual(self.post("/api/auth/login/", {"email": "john@example.com", "password": OLD_PW}, client=Client()).status_code, 400)
        self.assertEqual(self.post("/api/auth/login/", {"email": "john@example.com", "password": NEW_PW}, client=Client()).status_code, 200)

    def test_token_is_single_use(self):
        self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail()
        self.assertEqual(self.post(self.CONFIRM, {"token": token, "password": NEW_PW}).status_code, 200)
        r = self.post(self.CONFIRM, {"token": token, "password": "Another#Pass2028"})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_RESET_TOKEN"))

    def test_invalid_tokens_rejected(self):
        user = self.make_user()
        for bad in ("", "garbage", "no-dot-here", "MQ.badtoken", "!!!.???", "MQ.", ".abc", "99999.abc-def"):
            with self.subTest(bad):
                r = self.post(self.CONFIRM, {"token": bad, "password": NEW_PW})
                self.assertIn(r.status_code, (400,))
                self.assertIn(r.json()["code"], ("INVALID_RESET_TOKEN", "VALIDATION_ERROR"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(OLD_PW))

    def test_tampered_token_rejected(self):
        self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail()
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        self.assertEqual(self.post(self.CONFIRM, {"token": tampered, "password": NEW_PW}).json()["code"], "INVALID_RESET_TOKEN")

    def test_token_of_one_user_cannot_reset_another(self):
        self.make_user()
        other = self.make_user(email="other@example.com")
        self.post(self.REQ, {"email": "john@example.com"})
        uid_other = __import__("django.utils.http", fromlist=["x"]).urlsafe_base64_encode(str(other.pk).encode())
        token = self.token_from_mail().partition(".")[2]
        r = self.post(self.CONFIRM, {"token": f"{uid_other}.{token}", "password": NEW_PW})
        self.assertEqual(r.json()["code"], "INVALID_RESET_TOKEN")

    def test_expired_token_rejected(self):
        self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):  # everything issued before now is expired
            time.sleep(1.1)
            r = self.post(self.CONFIRM, {"token": token, "password": NEW_PW})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_RESET_TOKEN"))
        self.assertTrue(User.objects.get().check_password(OLD_PW))

    def test_weak_new_password_rejected_and_token_still_usable(self):
        self.make_user()
        self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail()
        for pw in ("123", "password", "12345678901", "john@example.com"):
            r = self.post(self.CONFIRM, {"token": token, "password": pw})
            self.assertEqual(r.status_code, 400, pw)
            self.assertIn("password", r.json()["fields"])
        self.assertTrue(User.objects.get().check_password(OLD_PW))
        self.assertEqual(self.post(self.CONFIRM, {"token": token, "password": NEW_PW}).status_code, 200)

    def test_missing_fields(self):
        r = self.post(self.CONFIRM, {})
        self.assertEqual(r.status_code, 400)
        self.assertIn("token", r.json()["fields"])
        self.assertIn("password", r.json()["fields"])

    def test_reset_invalidates_existing_sessions(self):
        self.make_user()
        logged_in = Client()
        self.post("/api/auth/login/", {"email": "john@example.com", "password": OLD_PW}, client=logged_in)
        self.assertTrue(logged_in.get("/api/auth/session/").json()["authenticated"])
        self.post(self.REQ, {"email": "john@example.com"})
        self.post(self.CONFIRM, {"token": self.token_from_mail(), "password": NEW_PW})
        self.assertFalse(logged_in.get("/api/auth/session/").json()["authenticated"])

    def test_google_only_account_can_set_a_password_via_reset(self):
        self.make_user(password=None, provider="google", google_sub="g-1")
        self.post(self.REQ, {"email": "john@example.com"})
        self.assertEqual(self.post(self.CONFIRM, {"token": self.token_from_mail(), "password": NEW_PW}).status_code, 200)
        self.assertTrue(User.objects.get().check_password(NEW_PW))

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(self.REQ, {"email": "a@b.com"}, content_type="application/json")
        self.assertEqual(r.json()["code"], "CSRF_FAILED")

    def test_request_is_rate_limited(self):
        statuses = [self.post(self.REQ, {"email": "x@example.com"}).status_code for _ in range(12)]
        self.assertEqual(statuses[:10], [200] * 10)
        self.assertEqual(statuses[10:], [429, 429])
        self.assertEqual(self.post(self.REQ, {"email": "x@example.com"}).json()["code"], "RATE_LIMITED")

    def test_smtp_failure_does_not_change_the_response(self):
        self.make_user()
        with mock.patch("apps.accounts.password_reset.send_mail", side_effect=OSError("smtp down")):
            r = self.post(self.REQ, {"email": "john@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "If an account exists for this email, password reset instructions have been sent.")

    def test_no_secrets_in_logs(self):
        self.make_user()
        with self.assertLogs("apps.accounts.password_reset", level="WARNING") as logs:
            self.post(self.REQ, {"email": "john@example.com"})
        token = self.token_from_mail().partition(".")[2]
        joined = "\n".join(logs.output)
        self.assertNotIn(token, joined)
        self.assertNotIn("john@example.com", joined)


# --- Change password ---

class ChangePasswordTests(ApiTestCase):
    URL = "/api/auth/change-password/"

    def login(self, client=None, **kw):
        user = self.make_user(**kw)
        c = client or self.c
        self.post("/api/auth/login/", {"email": user.email, "password": OLD_PW}, client=c)
        return user

    def test_requires_authentication(self):
        r = self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": NEW_PW})
        self.assertEqual((r.status_code, r.json()["code"]), (401, "NOT_AUTHENTICATED"))

    def test_wrong_current_password(self):
        user = self.login()
        r = self.post(self.URL, {"currentPassword": "wrong-pass-123", "newPassword": NEW_PW})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "INVALID_CURRENT_PASSWORD"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(OLD_PW))

    def test_weak_new_password(self):
        user = self.login()
        for pw in ("123", "password", "12345678901", "short1"):
            r = self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": pw})
            self.assertEqual(r.status_code, 400, pw)
            self.assertIn("newPassword", r.json()["fields"])
        user.refresh_from_db()
        self.assertTrue(user.check_password(OLD_PW))

    def test_new_password_must_differ(self):
        self.login()
        r = self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": OLD_PW})
        self.assertEqual(r.status_code, 400)

    def test_missing_fields(self):
        self.login()
        r = self.post(self.URL, {})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.json()["fields"]), {"currentPassword", "newPassword"})

    def test_success_changes_hash_and_keeps_current_session(self):
        user = self.login()
        r = self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": NEW_PW})
        self.assertEqual((r.status_code, r.json()), (200, {"success": True}))
        self.assertNotIn(NEW_PW, r.content.decode())
        user.refresh_from_db()
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertNotEqual(user.password, NEW_PW)
        self.assertTrue(user.check_password(NEW_PW))
        self.assertFalse(user.check_password(OLD_PW))
        self.assertTrue(self.c.get("/api/auth/session/").json()["authenticated"])  # this browser stays signed in
        self.assertEqual(self.post("/api/auth/login/", {"email": user.email, "password": OLD_PW}, client=Client()).status_code, 400)
        self.assertEqual(self.post("/api/auth/login/", {"email": user.email, "password": NEW_PW}, client=Client()).status_code, 200)

    def test_other_sessions_are_invalidated(self):
        other_browser = Client()
        self.login(client=other_browser)
        self.post("/api/auth/login/", {"email": "john@example.com", "password": OLD_PW})  # this.c
        self.assertTrue(other_browser.get("/api/auth/session/").json()["authenticated"])
        self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": NEW_PW})
        self.assertFalse(other_browser.get("/api/auth/session/").json()["authenticated"])
        self.assertTrue(self.c.get("/api/auth/session/").json()["authenticated"])

    def test_google_only_account_is_handled_deliberately(self):
        user = self.make_user(password=None, provider="google", google_sub="g-1")
        self.c.force_login(user)
        r = self.post(self.URL, {"currentPassword": "whatever12345", "newPassword": NEW_PW})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "NO_LOCAL_PASSWORD"))
        self.assertFalse(User.objects.get().has_usable_password())

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(self.URL, {"currentPassword": OLD_PW, "newPassword": NEW_PW}, content_type="application/json")
        self.assertEqual(r.json()["code"], "CSRF_FAILED")

    def test_passwords_never_logged(self):
        self.login()
        with self.assertNoLogs(level="DEBUG"):
            self.post(self.URL, {"currentPassword": OLD_PW, "newPassword": NEW_PW})


class DevEmailBackendTests(TestCase):
    def test_prints_decoded_link_verbatim(self):
        import io
        from django.core.mail import EmailMessage
        from .email_backends import ReadableConsoleEmailBackend
        link = "http://localhost:8080/site/pages/reset-password.html?token=MQ.abcd1-" + "f" * 40
        out = io.StringIO()
        sent = ReadableConsoleEmailBackend(stream=out).send_messages(
            [EmailMessage("Subj", f"open {link} now", "from@x.test", ["to@x.test"])])
        self.assertEqual(sent, 1)
        self.assertIn(link, out.getvalue())  # not quoted-printable mangled
        self.assertNotIn("=3D", out.getvalue())
        self.assertIn("NOT delivered", out.getvalue())

    @override_settings(DEBUG=True)
    def test_settings_default_backend_in_debug(self):
        import importlib, os
        from unittest import mock as m
        import config.settings as cfg
        with m.patch.dict(os.environ, {"DJANGO_DEBUG": "True", "EMAIL_BACKEND": ""}):
            reloaded = importlib.reload(cfg)
            self.assertTrue(reloaded.EMAIL_BACKEND.endswith("ReadableConsoleEmailBackend"))
        importlib.reload(cfg)


class ProfileApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="profile@example.com", password="Mkulima#2026safe", full_name="Original Name", phone="0712345678"
        )
        self.client.force_login(self.user)

    def test_profile_get_requires_authentication(self):
        anonymous = Client()
        response = anonymous.get("/api/profile/")
        self.assertEqual(response.status_code, 401)

    def test_profile_update_name_and_phone(self):
        response = self.client.put(
            "/api/profile/",
            {"fullName": "Updated Farmer", "phone": "+255700000001"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Farmer")
        self.assertEqual(self.user.phone, "+255700000001")
        self.assertEqual(response.json()["user"]["email"], "profile@example.com")
