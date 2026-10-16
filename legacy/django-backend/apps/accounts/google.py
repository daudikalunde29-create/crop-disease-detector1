"""Server-side verification of Google Sign-In ID tokens.

The frontend (Google Identity Services) sends the raw ID token to
POST /api/auth/google/. NOTHING in that request is trusted until this module has
verified it with Google's public keys. The token is used once, to establish who
the user is, and is then discarded: the application session is a Django session.

`verify_google_id_token` is the single seam the tests mock, so the test-suite
never needs the network.
"""
import logging

from django.conf import settings
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)

GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class GoogleNotConfigured(Exception):
    """GOOGLE_CLIENT_ID is not set on the server."""


class GoogleUnavailable(Exception):
    """Google's signing keys could not be fetched (network problem)."""


class GoogleTokenError(Exception):
    """The credential is invalid, expired, for another app, or unusable."""

    def __init__(self, reason="invalid"):
        super().__init__(reason)
        self.reason = reason


def verify_google_id_token(raw_token):
    """Verify `raw_token` with Google and return normalised, trusted claims:
    {"sub", "email", "name", "picture"}.

    Checked: signature (Google's certs), expiry/issued-at, issuer, audience == our
    GOOGLE_CLIENT_ID, presence of `sub`/`email`, and `email_verified is true`.
    """
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleNotConfigured()

    try:
        claims = id_token.verify_oauth2_token(
            raw_token, google_requests.Request(), client_id, clock_skew_in_seconds=10
        )
    except TransportError as exc:  # must precede GoogleAuthError (it is a subclass)
        logger.warning("Could not reach Google to verify an ID token: %s", exc)
        raise GoogleUnavailable() from exc
    except (ValueError, GoogleAuthError) as exc:
        # Malformed token, bad signature, expired, wrong audience or wrong issuer.
        raise GoogleTokenError("invalid") from exc

    # Defence in depth: re-assert the claims we rely on, even though the library checks most of them.
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleTokenError("issuer")
    aud = claims.get("aud")
    if aud != client_id:
        raise GoogleTokenError("audience")
    sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise GoogleTokenError("missing_claims")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleTokenError("email_unverified")

    return {
        "sub": sub,
        "email": email,
        "name": str(claims.get("name") or claims.get("given_name") or "").strip(),
        "picture": str(claims.get("picture") or "").strip(),
    }
