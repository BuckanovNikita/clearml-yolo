"""ClearML web addresses for source identities shown in readable reports."""

from typing import Any

from loguru import logger

from clearml_yolo.core.identity import IdentityLinks, ModelIdentity


def identity_links(task: Any, identity: ModelIdentity) -> IdentityLinks:
    """Build exact links from the invocation's session; links are optional presentation.

    Without the invocation's task no session exists, so the SDK is not touched and no
    network request can stall report rendering. URL-building failures never fail a report:
    the identity footer then shows plain readable text.
    """
    if task is None or (identity.training_task_id is None and identity.model_id is None):
        return IdentityLinks()
    try:
        # Deferred: ClearML import cost belongs to invocations that already own a task.
        from clearml import Task
        from clearml.backend_api.session import Session

        host = str(Session.get_app_server_host()).rstrip("/")
        # A pipeline trains and reports in one task; a report never links its own task.
        reporting_task = str(getattr(task, "id", ""))
        task_url = (
            str(Task.get_task_output_log_web_page(identity.training_task_id, app_server_host=host))
            if identity.training_task_id and identity.training_task_id != reporting_task
            else None
        )
        model_url = f"{host}/projects/*/models/{identity.model_id}" if identity.model_id else None
        return IdentityLinks(model_url=model_url, task_url=task_url)
    # The SDK raises assorted configuration and transport errors; a link is a convenience
    # whose absence is reported at DEBUG and rendered as plain text by the caller.
    except Exception as error:  # noqa: BLE001
        logger.debug("ClearML identity links unavailable for {}: {}", identity.label, type(error).__name__)
        return IdentityLinks()
