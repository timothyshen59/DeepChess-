import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router
from routes.coaching import router as coaching_router
from routes.predict import router as predict_router
from routes.opening import router as opening_router
from routes.opening_deviation import router as opening_deviation_router

from config import settings
from services.transformer import load_model
from services.stockfish import start_stockfish_pool, stop_stockfish_pool
from services.coaching.opening import opening_deps
from services.opening_deviation import deps as opening_deviation_deps

# Without this, logger.info(...) calls throughout the app (this module's
# startup diagnostics, services/stockfish.py's pool-startup log, etc.) are
# silently dropped -- Python's logging module only auto-prints WARNING and
# above when nothing configures a handler/level.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_stockfish_pool()
    load_model()
    opening_deviation_deps.load_deps()
    opening_deps.load_deps()
    yield
    await opening_deviation_deps.close_deps()
    opening_deps.close_deps()
    stop_stockfish_pool()


app = FastAPI(
    title="Chess Analysis API",
    description="Move annotation + Elo prediction",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Configurable via CORS_ALLOW_ORIGINS (config.py) -- defaults to the
    # local Vite dev server only, but a real deployment needs to set this
    # to the actual deployed frontend origin(s).
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(analyze_router)
app.include_router(coaching_router)
app.include_router(predict_router)
app.include_router(opening_router)
app.include_router(opening_deviation_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
