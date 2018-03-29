class AdmError(Exception):
    """Base class for ADM parsing exceptions."""
    pass


class AdmMissingRequiredElement(AdmError):
    """Exception raised for missing required elements.

    Parameters:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class AdmIDError(AdmError):
    """Exception raised when errors relating to IDs are identified.

    Parameters:
        message (str): explanation of the error
    """
    def __init__(self, message):
        self.message = message


class AdmWarning(Warning):
    """Base class for ADM parsing warnings."""
    pass


class AdmUnknownAttribute(AdmWarning):
    """Warning raised for unknown attributes

    Parameters:
        element -- the element containing the attribute
        attribute -- the unknown attribute
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class AdmIDWarning(AdmWarning):
    """Warning raised when issues relating to IDs are identified.

    Parameters:
        message (str): explanation of the error
    """
    def __init__(self, message):
        self.message = message
