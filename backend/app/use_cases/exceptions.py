class ApplicationError(Exception):
    """Base class for application-layer errors."""


class LedgerNotFoundError(ApplicationError):
    pass


class UserNotFoundError(ApplicationError):
    pass


class LedgerAccessConflictError(ApplicationError):
    pass


class CategoryGroupNotFoundError(ApplicationError):
    pass


class CategoryNotFoundError(ApplicationError):
    pass


class CategoryArchivedError(ApplicationError):
    pass


class DuplicateCategoryGroupError(ApplicationError):
    pass


class DuplicateCategoryError(ApplicationError):
    pass


class CategoryGroupArchivedError(ApplicationError):
    pass


class CategoryGroupHasActiveChildrenError(ApplicationError):
    pass


class CrossLedgerReferenceError(ApplicationError):
    pass


class DuplicateTemplateCodeError(ApplicationError):
    pass


class InvalidDefaultDueDayError(ApplicationError):
    pass
