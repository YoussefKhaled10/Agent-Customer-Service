class AuthenticationError(Exception):
    error_code = "authentication_error"
    status_code = 401


class InvalidCredentialsError(AuthenticationError):
    error_code = "invalid_credentials"


class InvalidTokenError(AuthenticationError):
    error_code = "invalid_token"


class InactiveCustomerError(AuthenticationError):
    error_code = "inactive_customer"
    status_code = 403


class EmailAlreadyRegisteredError(AuthenticationError):
    error_code = "email_already_registered"
    status_code = 409


class CustomerNotFoundError(AuthenticationError):
    error_code = "customer_not_found"
    status_code = 404
