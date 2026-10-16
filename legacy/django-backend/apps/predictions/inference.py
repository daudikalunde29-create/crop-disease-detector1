"""Boundary between the HTTP layer and the (future) AI inference engine.

M4.2 ships ONLY the boundary. No model exists yet, so the default engine reports
"not ready" and the API returns an honest not_ready response - it never invents a
disease, confidence, treatment or accuracy.

Later stages (M6 OpenCV preprocessing, M7 training, M8 TensorFlow inference)
add a real engine class and point settings.PREDICTION_ENGINE (env PREDICTION_ENGINE)
at it, without touching the view or the frontend contract.
"""
from dataclasses import asdict, dataclass

from django.conf import settings
from django.utils.module_loading import import_string

NOT_READY_MESSAGE = (
    "Prediction service is not available yet. "
    "The TensorFlow inference engine will be integrated in a later stage."
)


@dataclass(frozen=True)
class PredictionResult:
    """What a real engine must return. Fields come from the model, never from the API layer."""
    crop: str
    condition: str
    confidence: float  # percent, 0-100
    model_version: str

    def to_dict(self):
        return asdict(self)


class InferenceEngine:
    """Contract for inference engines."""

    def is_ready(self) -> bool:
        raise NotImplementedError

    def predict(self, image) -> PredictionResult:
        """`image` is an already-validated, fully decoded PIL.Image.Image."""
        raise NotImplementedError


class NullInferenceEngine(InferenceEngine):
    """Default until M8: no model is installed."""

    def is_ready(self):
        return False

    def predict(self, image):
        raise RuntimeError("No inference engine is installed.")


def get_inference_engine() -> InferenceEngine:
    return import_string(settings.PREDICTION_ENGINE)()
