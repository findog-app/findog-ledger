from pydantic import BaseModel


class ObligationStatusUpdateRequest(BaseModel):
    """
    Placeholder contract for a future integration endpoint.

    TODO: update obligation status by a stable business/public reference
    instead of an internal database primary key.
    """

    business_reference: str
    provider_status: str
    synced_at: str


class IntegrationSyncEventLog(BaseModel):
    """
    Placeholder payload for future sync event persistence.

    TODO: persist successful and failed sync attempts with provider payload
    references and failure diagnostics.
    """

    business_reference: str
    outcome: str
    detail: str | None = None
