from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.book import BookSearchResponse
from app.services.book_search import KakaoBookSearchService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/search", response_model=BookSearchResponse)
@limiter.limit("30/minute")
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, description="검색어"),
    page: int = Query(1, ge=1, le=50),
    size: int = Query(10, ge=1, le=50),
) -> BookSearchResponse:
    service = KakaoBookSearchService(request.app.state.http_client)
    return await service.search(q, page=page, size=size)
