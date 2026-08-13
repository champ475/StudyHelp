from fastapi import FastAPI

import studyhelp.verification  # noqa: F401  side effect: registers topic verifiers
from studyhelp.api.routes import health, problems, sessions
from studyhelp.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="StudyHelp API")
    app.include_router(health.router)
    app.include_router(problems.router)
    app.include_router(sessions.router)
    return app


app = create_app()
