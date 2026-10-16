from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def health(request):
    return Response({"status": "ok", "service": "crop-disease-detector", "backend": "django"})


def not_found(request, exception=None):
    return JsonResponse({"code": "NOT_FOUND", "message": "Endpoint not found."}, status=404)


def server_error(request):
    return JsonResponse({"code": "SERVER_ERROR", "message": "An unexpected server error occurred."}, status=500)
