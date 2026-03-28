import httpx

from app.cache.memory import inventory_cache
from app.models.inventory import ProviderResult, StoreStock
from app.providers.base import BaseProvider

CLIENT_ID = "546f189b39f0be980b43a5d16c006c09"
GUEST_LOGIN_URL = (
    "https://www.ypbooks.co.kr/back_login/base_login/api/v1/auth/login-guest"
)
SEARCH_URL = (
    "https://www.ypbooks.co.kr/back_shop/base_shop/api/v1"
    "/search_indexes/result/product"
)
STOCK_URL = (
    "https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/product/stock-info"
)

SEARCH_PARAMS = {
    "type": "product",
    "collection": "yp_product",
    "listCount": "1",
    "pageNumber": "1",
    "startDate": "1970.01.02",
    "sort": "RANK",
    "sortOrder": "DESC",
    "endType": "1,2,3,4,5,7",
    "searchType": "ON",
}


class YoungpoongProvider(BaseProvider):
    provider_name = "youngpoong"
    display_name = "영풍문고"

    _access_token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "clientId": CLIENT_ID,
            "platform": "PC",
            "accessToken": self._access_token or "",
        }

    async def _ensure_token(self) -> None:
        if self._access_token:
            return
        resp = await self.client.put(
            GUEST_LOGIN_URL,
            headers={"clientId": CLIENT_ID, "platform": "PC"},
            content=b"{}",
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("state") != "SUCCESS":
            raise RuntimeError(f"Guest login failed: {data.get('msg')}")
        self._access_token = data["data"]["accessToken"]

    async def _search_book(self, isbn13: str) -> tuple[str, str] | None:
        """ISBN -> (bookCd, productPrice) or None if not found."""
        params = {**SEARCH_PARAMS, "query": isbn13}
        resp = await self.client.get(
            SEARCH_URL, params=params, headers=self._headers()
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("state") != "SUCCESS":
            # Token may have expired — clear it and raise to trigger retry
            self._access_token = None
            raise RuntimeError(f"Search failed: {body.get('msg')}")
        items = body["data"]["ypProductResult"]["dataList"]
        if not items:
            return None
        first = items[0]
        return str(first["bookCd"]), str(first["productPrice"])

    async def search_by_isbn(self, isbn13: str) -> ProviderResult:
        cache_key = f"youngpoong:{isbn13}"
        if cache_key in inventory_cache:
            return inventory_cache[cache_key]

        try:
            await self._ensure_token()
            book_info = await self._search_book(isbn13)
            if not book_info:
                result = ProviderResult(
                    provider=self.provider_name,
                    display_name=self.display_name,
                    status="success",
                    stores=[],
                )
                inventory_cache[cache_key] = result
                return result

            book_cd, price = book_info
            resp = await self.client.get(
                STOCK_URL,
                params={"iBookCd": book_cd, "iNorPrc": price, "iGubun": "1"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            body = resp.json()

            stores = [
                StoreStock(
                    store_name=f"영풍문고 {s['werksNm']}",
                    has_stock=True,
                    quantity=s["labst"],
                )
                for s in body.get("data", [])
                if s.get("labst", 0) > 0
            ]

            result = ProviderResult(
                provider=self.provider_name,
                display_name=self.display_name,
                status="success",
                stores=stores,
            )
        except httpx.TimeoutException:
            result = ProviderResult(
                provider=self.provider_name,
                display_name=self.display_name,
                status="timeout",
                error_message="요청 시간 초과",
            )
        except Exception as e:
            result = ProviderResult(
                provider=self.provider_name,
                display_name=self.display_name,
                status="error",
                error_message=str(e),
            )

        if result.status == "success":
            inventory_cache[cache_key] = result
        return result
