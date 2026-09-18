class ToolError(Exception):
    """Base exception for tool registration and execution failures."""

    error_code = "tool_error"


class ToolRegistrationError(ToolError):
    error_code = "tool_registration_error"


class ToolNotFoundError(ToolError):
    error_code = "tool_not_found"


class ToolValidationError(ToolError):
    error_code = "invalid_tool_arguments"


class ToolAuthenticationRequiredError(ToolError):
    error_code = "authentication_required"


class ToolConfirmationRequiredError(ToolError):
    error_code = "confirmation_required"


class ToolExecutionError(ToolError):
    error_code = "tool_execution_error"
