from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


def user_payload(user):
    """User shape expected by public/site/js/auth.js. Never includes the password."""
    return {
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "provider": user.provider,
        "createdAt": user.created_at.isoformat(),
    }


class RegisterSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs["email"], full_name=attrs["fullName"])
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, data):
        return User.objects.create_user(
            email=data["email"],
            password=data["password"],
            full_name=data["fullName"],
            phone=data.get("phone", ""),
            role=User.Role.FARMER,
            provider=User.Provider.EMAIL,
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    remember = serializers.BooleanField(required=False, default=False)


class GoogleAuthSerializer(serializers.Serializer):
    # A Google ID token is a ~1-2 KB JWT; the cap just stops absurd payloads.
    credential = serializers.CharField(max_length=8192, trim_whitespace=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    currentPassword = serializers.CharField(write_only=True, trim_whitespace=False)
    newPassword = serializers.CharField(write_only=True, trim_whitespace=False)


class ProfileUpdateSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=150, trim_whitespace=True)
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")

    def validate_fullName(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()
