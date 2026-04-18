class AppError(Exception):
    pass


class DuplicateNameError(AppError):
    pass


class MaxPendingDraftsError(AppError):
    pass


class UnsupportedFileTypeError(AppError):
    pass


class FileTooLargeError(AppError):
    pass


class FilenameRequiredError(AppError):
    pass


class DraftNotFoundError(AppError):
    pass


class DraftNotEditableError(AppError):
    pass


class DraftNotPendingError(AppError):
    pass