"""Local System One gateway: POST /v1/systemone, GET /v1/models."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import Settings, settings
from app.proxy import UpstreamClient, UpstreamError
from app.schemas import ModelMetadata, ModelMetadataList, SystemOneRequest


def get_settings() -> Settings:
    return settings


upstream = UpstreamClient(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await upstream.start()
    try:
        yield
    finally:
        await upstream.stop()


app = FastAPI(
    title="Local System One Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


async def require_gateway_auth(
    authorization: str | None = Header(default=None),
    cfg: Settings = Depends(get_settings),
) -> None:
    if not cfg.gateway_api_key:
        return
    expected = f"Bearer {cfg.gateway_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/healthz")
async def healthz(cfg: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "status": "ok",
        "upstream": cfg.upstream_origin,
        "default_model": cfg.default_model,
    }


@app.post("/v1/systemone")
async def systemone(
    body: SystemOneRequest,
    _: None = Depends(require_gateway_auth),
    cfg: Settings = Depends(get_settings),
) -> JSONResponse:
    payload = body.model_dump(mode="json", exclude_none=True)
    if not payload.get("model"):
        payload["model"] = cfg.default_model

    try:
        result = await upstream.post_systemone(payload)
    except UpstreamError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.body)
    except Exception as exc:  # noqa: BLE001 — surface upstream connectivity failures
        raise HTTPException(
            status_code=502,
            detail=f"upstream request failed: {exc}",
        ) from exc

    return JSONResponse(content=result)


@app.get("/v1/models", response_model=None)
async def list_models(
    request: Request,
    _: None = Depends(require_gateway_auth),
    cfg: Settings = Depends(get_settings),
) -> JSONResponse:
    # Prefer upstream listing when it looks TypeSafe-shaped; otherwise curated.
    try:
        status, body = await upstream.get_models()
    except Exception:
        return JSONResponse(content=_curated_models(cfg))

    if status == 200 and isinstance(body, dict) and "models" in body:
        models = body.get("models")
        if isinstance(models, list) and models:
            # TypeSafe style: [{name, description, ...}]
            if isinstance(models[0], dict) and "name" in models[0]:
                return JSONResponse(content=body)
        return JSONResponse(content=_curated_models(cfg))

    # OpenRouter and similar return OpenAI-shaped lists — use curated catalog.
    _ = request
    return JSONResponse(content=_curated_models(cfg))


def _curated_models(cfg: Settings) -> dict[str, Any]:
    return ModelMetadataList(
        models=[
            ModelMetadata(
                name=name,
                description=f"Curated System One model alias ({cfg.upstream_origin})",
            )
            for name in cfg.curated_models
        ]
    ).model_dump(mode="json")
