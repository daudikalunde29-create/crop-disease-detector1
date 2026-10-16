import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def json_exception_handler(exc, context):
    """Every API error becomes {code, message} — no stack traces leak."""
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error")
        return Response({"code": "SERVER_ERROR", "message": "An unexpected server error occurred."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, exceptions.NotAuthenticated):
        code, message = "NOT_AUTHENTICATED", "Authentication required. Please log in."
    elif isinstance(exc, exceptions.PermissionDenied) and "CSRF" in str(exc.detail):
        code, message = "CSRF_FAILED", "Security check failed (CSRF). Refresh the page and try again."
    elif isinstance(exc, exceptions.PermissionDenied):
        code, message = "PERMISSION_DENIED", "You do not have permission to do this."
    elif isinstance(exc, exceptions.ParseError):
        code, message = "INVALID_JSON", "Request body must be valid JSON."
    elif isinstance(exc, exceptions.Throttled):
        code, message = "RATE_LIMITED", "Too many requests. Please wait a while and try again."
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        code, message = "UNSUPPORTED_MEDIA_TYPE", "Unsupported request content type."
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code, message = "METHOD_NOT_ALLOWED", str(exc.detail)
    else:
        code, message = "ERROR", str(getattr(exc, "detail", "Request failed."))
    response.data = {"code": code, "message": message}
    return response
