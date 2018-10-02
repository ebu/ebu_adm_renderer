class AdmError(Exception):
    """Base class for ADM parsing exceptions."""


class AdmMissingRequiredElement(AdmError):
    """Exception raised for missing required elements."""


class AdmIDError(AdmError):
    """Exception raised when errors relating to IDs are identified."""


class AdmWarning(Warning):
    """Base class for ADM parsing warnings."""


class AdmUnknownAttribute(AdmWarning):
    """Warning raised for unknown attributes."""


class AdmIDWarning(AdmWarning):
    """Warning raised when issues relating to IDs are identified."""
