"""Server-controlled password reset.

Uses Django's PasswordResetTokenGenerator: a stateless HMAC token bound to the
user's current password hash, last_login and a timestamp. Consequences:
  * nothing is stored in the database (no plaintext or hashed tokens to leak);
  * a token stops working the moment the password changes (single use);
  * it expires after settings.PASSWORD_RESET_TIMEOUT seconds.

The value handed to the user is "<uidb64>.<token>" so the existing frontend
contract {token, password} needs no extra field.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User

logger = logging.getLogger(__name__)

# Substrings identifying email backends that never deliver to a real inbox.
_NON_DELIVERING = ("console", "locmem", "dummy", "filebased")


def make_reset_token(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f"{uid}.{default_token_generator.make_token(user)}"


def resolve_reset_token(value):
    """Return the active user the token belongs to, or None (bad format, unknown user, bad/expired token)."""
    if not isinstance(value, str) or "." not in value:
        return None
    uid, _, token = value.strip().partition(".")
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    if not user.is_active or not default_token_generator.check_token(user, token):
        return None
    return user


def send_reset_email(user):
    """Email reset instructions. Returns True if the backend accepted the message.
    Never logs the token or the address, and never raises (callers must give a generic response)."""
    token = make_reset_token(user)
    link = f"{settings.FRONTEND_ORIGIN}/site/pages/reset-password.html?token={token}"
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    body = (
        f"Hello {user.full_name or 'there'},\n\n"
        "We received a request to reset the password of your Crop Disease Detector account.\n\n"
        f"Open this link to choose a new password (valid for {minutes} minutes):\n{link}\n\n"
        "If the link does not open, paste this reset code on the reset page instead:\n"
        f"{token}\n\n"
        "If you did not ask for this, you can ignore this email; your password will not change.\n"
    )
    try:
        sent = send_mail("Reset your Crop Disease Detector password", body,
                         settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:  # SMTP down, bad credentials... must not change the HTTP response
        logger.exception("Password reset email could not be sent (user id=%s).", user.pk)
        return False
    if any(name in settings.EMAIL_BACKEND.lower() for name in _NON_DELIVERING):
        logger.warning("Password reset email for user id=%s went to the non-delivering email backend '%s'; "
                       "it was NOT delivered to a real inbox.", user.pk, settings.EMAIL_BACKEND.rsplit(".", 1)[-1])
    return bool(sent)
