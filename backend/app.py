import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.lib.asset_managers.factory import AssetManagerFactory
from backend.lib.utils import none_throws
from backend.path_manager import PathManager
from backend.route_handlers.base import RouteHandler
from backend.route_handlers.debug import DebugHandler
from backend.route_handlers.timelens_api import TimelensAPIHandler

# Configure logging environment
ENV = os.getenv("ENV", "development").lower()

if ENV == "production":
    logging_level = logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
else:  # development, testing, etc.
    logging_level = logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(level=logging_level, format=log_format)

# Load environment-specific file
env_file = ".env.prod" if os.getenv("ENV") == "production" else ".env.dev"
loaded = load_dotenv(dotenv_path=PathManager().get_repo_root() / env_file)
assert loaded, "Env not loaded"


sentry_sdk.init(
    dsn=none_throws(os.getenv("SENTRY_DSN")),
    send_default_pii=True,
    environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
)


class TimelensApp:
    ENABLED_ROUTE_HANDLERS_CLS: list[type[RouteHandler]] = [
        DebugHandler,
        TimelensAPIHandler,
    ]

    def __init__(self) -> None:
        self.path_manager = PathManager()
        self.asset_manager = AssetManagerFactory.create()

        self.app: FastAPI = FastAPI(lifespan=self.lifespan)

        for route_handler_cls in TimelensApp.ENABLED_ROUTE_HANDLERS_CLS:
            self.app.include_router(route_handler_cls(self).get_router())

        self.app.mount(
            "/assets",  # <- this goes first
            StaticFiles(directory=PathManager().get_assets_root()),
            name="assets",
        )

    @asynccontextmanager
    async def lifespan(self, _app: FastAPI) -> AsyncGenerator[None, None]:
        print("Server initializing...")
        print("Server initialize complete...")
        yield
        print("Server cleaning up...")
        print("Server cleanup complete...")


timelens_app = TimelensApp()
app = timelens_app.app
