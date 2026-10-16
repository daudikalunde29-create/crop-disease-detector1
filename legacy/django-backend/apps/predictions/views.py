import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .inference import NOT_READY_MESSAGE, get_inference_engine
from .validators import UploadRejected, validate_image_upload

logger = logging.getLogger(__name__)

# Allowance for multipart boundaries/headers on top of the file itself.
_MULTIPART_OVERHEAD = 64 * 1024


def _error(code, message, http_status):
    return Response({"code": code, "message": message}, status=http_status)


class PredictView(APIView):
    """POST /api/predict/  (multipart/form-data, field "image").

    M4.2: authenticated, validated upload + a clean inference boundary.
    There is NO model yet, so a valid image gets an honest `not_ready` answer.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # Refuse oversized bodies before Django parses (and buffers) them.
        try:
            declared = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            declared = 0
        if declared > settings.PREDICT_MAX_UPLOAD_BYTES + _MULTIPART_OVERHEAD:
            mb = settings.PREDICT_MAX_UPLOAD_BYTES / 1024 / 1024
            return _error("FILE_TOO_LARGE", f"The image is too large. The maximum size is {mb:g} MB.",
                          status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        try:
            uploaded = request.FILES.get("image")
        except ParseError:
            return _error("INVALID_UPLOAD", "The upload could not be read. Send multipart/form-data.",
                          status.HTTP_400_BAD_REQUEST)

        try:
            image = validate_image_upload(uploaded)
        except UploadRejected as rejected:
            return _error(rejected.code, rejected.message, rejected.http_status)

        engine = get_inference_engine()
        if not engine.is_ready():
            image.close()
            return Response({"status": "not_ready", "message": NOT_READY_MESSAGE},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Reached only once a real engine is installed (M8). The result comes from the model.
        try:
            result = engine.predict(image)
        except Exception:
            logger.exception("Inference engine failed.")
            return _error("INFERENCE_FAILED", "The prediction could not be completed.",
                          status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            image.close()
        return Response({"status": "ok", "prediction": result.to_dict()})
