from django.conf import settings
from django.contrib.auth import authenticate, login, logout, password_validation, update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .google import GoogleNotConfigured, GoogleTokenError, GoogleUnavailable, verify_google_id_token
from .models import User
from .password_reset import resolve_reset_token, send_reset_email
from .serializers import (
    ChangePasswordSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    user_payload,
)


def _error(code, message, http_status, fields=None):
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response(body, status=http_status)


def _validation_error(serializer):
    fields = {k: [str(m) for m in v] for k, v in serializer.errors.items()}
    first_field, msgs = next(iter(fields.items()))
    label = "" if first_field == "non_field_errors" else f"{first_field}: "
    return _error("VALIDATION_ERROR", f"{label}{msgs[0]}", status.HTTP_400_BAD_REQUEST, fields)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            if "email" in serializer.errors and any(
                "already exists" in str(m) for m in serializer.errors["email"]
            ):
                return _error("EMAIL_EXISTS", "An account with this email already exists.",
                              status.HTTP_409_CONFLICT)
            return _validation_error(serializer)
        user = serializer.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": user_payload(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)
        data = serializer.validated_data
        user = authenticate(request, username=data["email"].strip().lower(), password=data["password"])
        if user is None:
            return _error("AUTH_ERROR", "Invalid email or password.", status.HTTP_400_BAD_REQUEST)
        login(request, user)
        # remember=False -> session ends when the browser closes.
        request.session.set_expiry(None if data["remember"] else 0)
        return Response({"user": user_payload(user)})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)  # flushes the server-side session
        return Response({"success": True})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    """Also guarantees the csrftoken cookie exists for subsequent POSTs."""
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response({"authenticated": True, "user": user_payload(request.user)})
        return Response({"authenticated": False})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": user_payload(request.user)})


# --- M4.2: Google Sign-In ---------------------------------------------------

class GoogleConfigView(APIView):
    """Public Google OAuth Client ID, so the frontend and backend share ONE setting
    (GOOGLE_CLIENT_ID in backend/.env). A client ID is public by design; there is no secret here."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"enabled": bool(settings.GOOGLE_CLIENT_ID), "clientId": settings.GOOGLE_CLIENT_ID})


class GoogleAccountConflict(Exception):
    """The email belongs to an account already linked to a different Google identity."""


def _google_find_or_create(claims):
    """Resolve the Django user for verified Google claims. Returns (user, created, linked).

    1. Known Google account (google_sub)  -> that user.
    2. Same verified email, existing account -> LINK it to this Google identity. Google has proven
       the person controls the mailbox, but our own email/password sign-up never verified it, so the
       old local password is discarded (set_unusable_password) - otherwise someone who pre-registered
       a victim's address could keep password access after the victim signs in with Google. This also
       invalidates that account's existing sessions. The owner can set a new password via password reset.
    3. Otherwise -> create a new farmer account (provider=google, no local password).
    Raises GoogleAccountConflict if the email's account is already tied to a different Google identity.
    """
    sub, email = claims["sub"], claims["email"]

    user = User.objects.filter(google_sub=sub).first()
    if user:
        return user, False, False

    user = User.objects.filter(email__iexact=email).first()
    if user:
        if user.google_sub and user.google_sub != sub:
            raise GoogleAccountConflict()
        user.google_sub = sub
        user.provider = User.Provider.GOOGLE
        if claims["picture"] and not user.picture_url:
            user.picture_url = claims["picture"][:500]
        if user.has_usable_password():
            user.set_unusable_password()
        user.save()
        return user, False, True

    name = (claims["name"] or email.split("@")[0])[:150]
    user = User.objects.create_user(
        email=email, password=None, full_name=name, role=User.Role.FARMER,
        provider=User.Provider.GOOGLE, google_sub=sub, picture_url=claims["picture"][:500],
    )
    return user, True, False


class GoogleAuthView(APIView):
    """POST /api/auth/google/  {credential: <Google ID token>}  ->  Django session + {user}."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)

        try:
            claims = verify_google_id_token(serializer.validated_data["credential"])
        except GoogleNotConfigured:
            return _error("GOOGLE_NOT_CONFIGURED", "Google sign-in is not configured on the server.",
                          status.HTTP_503_SERVICE_UNAVAILABLE)
        except GoogleUnavailable:
            return _error("GOOGLE_UNAVAILABLE", "Could not reach Google to verify your sign-in. Please try again.",
                          status.HTTP_503_SERVICE_UNAVAILABLE)
        except GoogleTokenError as exc:
            if exc.reason == "email_unverified":
                return _error("GOOGLE_EMAIL_UNVERIFIED", "Your Google email address is not verified.",
                              status.HTTP_400_BAD_REQUEST)
            return _error("INVALID_GOOGLE_TOKEN", "Google sign-in failed: the credential could not be verified.",
                          status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                user, created, linked = _google_find_or_create(claims)
        except GoogleAccountConflict:
            return _error("GOOGLE_ACCOUNT_CONFLICT",
                          "This email is already linked to a different Google account.", status.HTTP_409_CONFLICT)
        except IntegrityError:
            # Two simultaneous first sign-ins: the other request won the insert; use its user.
            user = User.objects.filter(google_sub=claims["sub"]).first() or User.objects.filter(
                email__iexact=claims["email"]).first()
            created = linked = False
            if user is None:
                raise

        if not user.is_active:
            return _error("ACCOUNT_DISABLED", "This account has been disabled.", status.HTTP_403_FORBIDDEN)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": user_payload(user), "created": created, "linked": linked})


# --- M4.2: password reset / change ------------------------------------------

RESET_REQUEST_MESSAGE = "If an account exists for this email, password reset instructions have been sent."


class PasswordResetRequestView(APIView):
    """Always answers the same way, whether or not the email has an account (no enumeration)."""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password-reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)
        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_reset_email(user)
        return Response({"success": True, "message": RESET_REQUEST_MESSAGE})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password-reset-confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)
        data = serializer.validated_data

        user = resolve_reset_token(data["token"])
        if user is None:
            return _error("INVALID_RESET_TOKEN", "This reset link is invalid or has expired. Please request a new one.",
                          status.HTTP_400_BAD_REQUEST)
        try:
            password_validation.validate_password(data["password"], user)
        except DjangoValidationError as exc:
            msgs = list(exc.messages)
            return _error("VALIDATION_ERROR", f"password: {msgs[0]}", status.HTTP_400_BAD_REQUEST,
                          {"password": msgs})

        user.set_password(data["password"])
        user.save(update_fields=["password"])  # also kills this token and every existing session of the user
        return Response({"success": True, "message": "Your password has been updated. You can now log in."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change-password"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)
        current, new = serializer.validated_data["currentPassword"], serializer.validated_data["newPassword"]
        user = request.user

        if not user.has_usable_password():
            return _error("NO_LOCAL_PASSWORD",
                          "This account signs in with Google and has no password yet. "
                          "Use \"Forgot password\" to create one.", status.HTTP_400_BAD_REQUEST)
        if not user.check_password(current):
            return _error("INVALID_CURRENT_PASSWORD", "Your current password is incorrect.",
                          status.HTTP_400_BAD_REQUEST)
        if new == current:
            return _error("VALIDATION_ERROR", "newPassword: The new password must be different from the current one.",
                          status.HTTP_400_BAD_REQUEST, {"newPassword": ["The new password must be different from the current one."]})
        try:
            password_validation.validate_password(new, user)
        except DjangoValidationError as exc:
            msgs = list(exc.messages)
            return _error("VALIDATION_ERROR", f"newPassword: {msgs[0]}", status.HTTP_400_BAD_REQUEST,
                          {"newPassword": msgs})

        user.set_password(new)
        user.save(update_fields=["password"])
        # Keep THIS browser logged in; every other session of the user becomes invalid.
        update_session_auth_hash(request, user)
        return Response({"success": True})


class ProfileView(APIView):
    """Read/update safe profile fields for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": user_payload(request.user)})

    def put(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer)
        user = request.user
        user.full_name = serializer.validated_data["fullName"]
        user.phone = serializer.validated_data.get("phone", "")
        user.save(update_fields=["full_name", "phone"])
        return Response({"user": user_payload(user)})
