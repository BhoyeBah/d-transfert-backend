from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_message: str = "Une erreur est survenue."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Ressource introuvable."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Action non autorisée."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentification requise."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Conflit : cette action a déjà été traitée."


class UnbalancedOperationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_message = "L'opération n'est pas équilibrée (total entrées != total sorties)."


class InsufficientBalanceError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_message = "Solde insuffisant."


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erreur interne du serveur."},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
