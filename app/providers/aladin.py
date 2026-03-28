import httpx

from app.cache.memory import inventory_cache
from app.config import settings
from app.models.inventory import ProviderResult, StoreStock
from app.providers.base import BaseProvider


class AladinProvider(BaseProvider):
    provider_name = "aladin"
    display_name = "알라딘 중고매장"
    API_URL = "http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx"

    async def search_by_isbn(self, isbn13: str) -> ProviderResult:
        if not settings.aladin_ttb_key:
            return ProviderResult(
                provider=self.provider_name,
                display_name=self.display_name,
                status="error",
                error_message="ALADIN_TTB_KEY가 설정되지 않았습니다",
            )

        cache_key = f"aladin:{isbn13}"
        if cache_key in inventory_cache:
            return inventory_cache[cache_key]

        try:
            resp = await self.client.get(
                self.API_URL,
                params={
                    "ttbkey": settings.aladin_ttb_key,
                    "itemIdType": "ISBN13",
                    "ItemId": isbn13,
                    "output": "js",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            stores = []
            for item in data.get("itemOffStoreList", []):
                stores.append(
                    StoreStock(
                        store_name=item.get("offName", ""),
                        has_stock=True,
                        address=item.get("offAddress", None),
                    )
                )

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
