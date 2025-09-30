class AppException(Exception):
    """应用程序异常基类"""

    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(AppException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR", 401)


class AuthorizationError(AppException):
    """授权错误"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "PERMISSION_DENIED", 403)


class NotFoundError(AppException):
    """资源不存在错误"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class ValidationError(AppException):
    """数据验证错误"""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR", 422)


class BusinessError(AppException):
    """业务逻辑错误"""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        super().__init__(message, code, 400)


class DatabaseError(AppException):
    """数据库错误"""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, "DATABASE_ERROR", 500)
