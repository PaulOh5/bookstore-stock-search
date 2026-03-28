import httpx

from app.cache.memory import search_cache
from app.config import settings
from app.models.book import BookSearchResponse, BookSearchResult


class KakaoBookSearchService:
    API_URL = "https://dapi.kakao.com/v3/search/book"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def search(self, query: str, page: int = 1, size: int = 10) -> BookSearchResponse:
        if not settings.kakao_api_key:
            raise ValueError("KAKAO_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        cache_key = f"search:{query}:{page}:{size}"
        if cache_key in search_cache:
            return search_cache[cache_key]

        resp = await self.client.get(
            self.API_URL,
            params={"query": query, "page": page, "size": size},
            headers={"Authorization": f"KakaoAK {settings.kakao_api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()

        books = []
        for doc in data.get("documents", []):
            isbn13 = self._extract_isbn13(doc.get("isbn", ""))
            if not isbn13:
                continue
            books.append(
                BookSearchResult(
                    title=doc.get("title", ""),
                    authors=doc.get("authors", []),
                    isbn13=isbn13,
                    publisher=doc.get("publisher", ""),
                    price=doc.get("price", 0),
                    sale_price=doc.get("sale_price", 0),
                    thumbnail=doc.get("thumbnail", ""),
                    pub_date=doc.get("datetime", "")[:10],
                )
            )

        meta = data.get("meta", {})
        result = BookSearchResponse(
            books=books,
            total_count=meta.get("total_count", 0),
            is_end=meta.get("is_end", True),
            page=page,
        )
        search_cache[cache_key] = result
        return result

    @staticmethod
    def _extract_isbn13(isbn_str: str) -> str:
        """Kakao returns 'ISBN10 ISBN13' space-separated. Extract the 13-digit one."""
        for part in isbn_str.split():
            if len(part) == 13 and part.isdigit():
                return part
        # Fallback: return whatever is available
        stripped = isbn_str.strip()
        return stripped if stripped else ""
