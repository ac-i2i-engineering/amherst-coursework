"""Template context processors for global template settings."""

from django.conf import settings


def google_analytics(request):
    """Expose GA settings to all templates."""
    return {
        "ga_enabled": getattr(settings, "GA_ENABLED", False),
        "ga_measurement_id": getattr(settings, "GA_MEASUREMENT_ID", ""),
    }
