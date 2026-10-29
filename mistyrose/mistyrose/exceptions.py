from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    DRF's handler, plus Django model/lookup validation errors (for example a
    malformed UUID in a URL) turned into a 400 instead of an unhandled 500.
    """
    if isinstance(exc, DjangoValidationError):
        return Response({"error": "Invalid request.", "detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
    return drf_exception_handler(exc, context)
