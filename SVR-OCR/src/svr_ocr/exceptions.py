class SVROCRError(Exception):
    """Base exception for the SVR-OCR package."""


class PromptResolutionError(SVROCRError):
    """Raised when a prompt template cannot be resolved."""


class VerificationError(SVROCRError):
    """Raised when verification cannot be completed."""


class EndpointConfigurationError(SVROCRError):
    """Raised when an endpoint-backed transcriber is missing required settings."""


class TranscriptionError(SVROCRError):
    """Raised when the endpoint-backed transcriber cannot produce candidates."""
