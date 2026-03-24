from typing import Protocol

from app.schemas.integration import (
    IntegrationSyncEventLog,
    ObligationStatusUpdateRequest,
)


class IntegrationSyncRecorder(Protocol):
    """Future persistence port for integration sync attempts."""

    def record(self, event: IntegrationSyncEventLog) -> None: ...


class ObligationStatusUpdater(Protocol):
    """
    Future port for integration-driven obligation updates.

    TODO: resolve obligations by stable business reference and append status
    event history instead of mutating by internal primary key alone.
    """

    def update_status(self, request: ObligationStatusUpdateRequest) -> None: ...
