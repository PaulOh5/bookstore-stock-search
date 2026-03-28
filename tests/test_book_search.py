import pytest
import respx
from httpx import Response

from app.services.book_search import KakaoBookSearchService


class TestExtractIsbn13:
    def test_extracts_isbn13_from_pair(self):
        assert KakaoBookSearchService._extract_isbn13("8983920998 9788983920997") == "9788983920997"

    def test_extracts_isbn13_only(self):
        assert KakaoBookSearchService._extract_isbn13("9788983920997") == "9788983920997"

    def test_returns_empty_for_empty(self):
        assert KakaoBookSearchService._extract_isbn13("") == ""

    def test_fallback_to_isbn10(self):
        assert KakaoBookSearchService._extract_isbn13("8983920998") == "8983920998"


@pytest.mark.asyncio
@respx.mock
async def test_search_books(client):
    respx.get("https://dapi.kakao.com/v3/search/book").mock(
        return_value=Response(200, json={
            "meta": {"total_count": 1, "is_end": True},
            "documents": [
                {
                    "title": "테스트 책",
                    "authors": ["저자"],
                    "isbn": "1234567890 9781234567890",
                    "publisher": "출판사",
                    "price": 15000,
                    "sale_price": 13500,
                    "thumbnail": "https://example.com/thumb.jpg",
                    "datetime": "2024-01-15T00:00:00.000+09:00",
                }
            ],
        })
    )

    resp = await client.get("/api/search", params={"q": "테스트"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["books"]) == 1
    assert data["books"][0]["isbn13"] == "9781234567890"
    assert data["books"][0]["title"] == "테스트 책"
