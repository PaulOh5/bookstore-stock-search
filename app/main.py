from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.routes import health, inventory, search
from app.config import settings
from app.providers.aladin import AladinProvider
from app.providers.kyobo import KyoboProvider
from app.providers.youngpoong import YoungpoongProvider
from app.services.book_search import KakaoBookSearchService
from app.services.inventory_aggregator import InventoryAggregator

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(timeout=settings.provider_timeout)
    app.state.http_client = client
    app.state.aggregator = InventoryAggregator(
        providers=[
            AladinProvider(client),
            KyoboProvider(client),
            YoungpoongProvider(client),
        ]
    )
    yield
    await client.aclose()


app = FastAPI(title="Off-Book-Search", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(search.router)
app.include_router(inventory.router)
app.include_router(health.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    books = []
    error = None
    if q:
        try:
            service = KakaoBookSearchService(request.app.state.http_client)
            result = await service.search(q)
            books = result.books
        except ValueError as e:
            error = str(e)
        except Exception:
            error = "책 검색 중 오류가 발생했습니다."
    return templates.TemplateResponse(
        request, "results.html", {"q": q, "books": books, "error": error}
    )
