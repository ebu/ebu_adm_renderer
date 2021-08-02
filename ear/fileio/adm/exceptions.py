from attr import attrib, attrs


class AdmError(Exception):
    """Base class for ADM parsing exceptions."""


class AdmMissingRequiredElement(AdmError):
    """Exception raised for missing required elements."""


class AdmIDError(AdmError):
    """Exception raised when errors relating to IDs are identified."""


@attrs(str=False)
class AdmFormatRefError(AdmError):
    """Error in references between ADM content and format parts."""
    message = attrib()
    reasons = attrib()

    def __str__(self):
        fmt = "{message}. Possible reasons:\n{reasons}" if self.reasons else "{message}"

        return fmt.format(
            message=self.message,
            reasons="\n".join("- {reason}".format(reason=reason)
                              for reason in self.reasons),
        )


class AdmWarning(Warning):
    """Base class for ADM parsing warnings."""


class AdmUnknownAttribute(AdmWarning):
    """Warning raised for unknown attributes."""


class AdmIDWarning(AdmWarning):
    """Warning raised when issues relating to IDs are identified."""
