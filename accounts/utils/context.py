from typing import Iterable, Any

from django.http import HttpRequest
from django.urls import reverse

from core.models import VirtualClock
import logging

logger = logging.getLogger(__name__)

def clocks_list_context(
    request: HttpRequest,
    clocks: Iterable[VirtualClock],
) -> dict[str, Any]:
    retrieve_url_name = "api-1.0.0:api-retrieve-clock"

    clock_api_urls = {
        clock.id: request.build_absolute_uri(
            reverse(retrieve_url_name, kwargs={"clock_id": clock.id})
        )
        for clock in clocks
    }

    context = {
        "clock_api_urls_retrieve": clock_api_urls,
        "clock_api_url_update": request.build_absolute_uri(
            reverse("api-1.0.0:api-update-clock")
        ),
    }

    logger.debug(
        "clocks_list_context: retrieve=%s update=%s",
        clock_api_urls,
        context["clock_api_url_update"],
    )

    return context
