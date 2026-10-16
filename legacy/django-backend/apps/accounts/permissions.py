from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Server-side role check (role lives on the user row, never trusted from the client)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")
