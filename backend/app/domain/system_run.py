from enum import StrEnum


class TaskRunMode(StrEnum):
    DISABLED = "disabled"
    MANUAL_ONLY = "manual_only"
    SCHEDULED = "scheduled"


class SystemRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


class SystemRunStepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class SystemRunSkipReason(StrEnum):
    DISABLED = "disabled"
    MANUAL_ONLY = "manual_only"
    NOT_DUE = "not_due"
    NOT_CONFIGURED = "not_configured"
    NO_ELIGIBLE_TARGETS = "no_eligible_targets"
    PREREQUISITE_FAILED = "prerequisite_failed"
