"""Root entrypoint — run with: python main.py"""
import uvicorn
from app.config import SETTINGS

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host=SETTINGS.APP_HOST,
        port=SETTINGS.APP_PORT,
        reload=SETTINGS.UVICORN_RELOAD,
        log_level=SETTINGS.LOG_LEVEL.lower(),
    )
