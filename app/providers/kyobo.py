import asyncio
import json
import re

import httpx

from app.cache.memory import inventory_cache
from app.models.inventory import ProviderResult, StoreStock
from app.providers.base import BaseProvider

KIOSK_URL = "https://kiosk.kyobobook.co.kr/bookInfoInk"

STORES: dict[str, str] = {
    "001": "광화문",
    "003": "원그로브",
    "015": "강남",
    "023": "건대스타시티",
    "029": "잠실",
    "033": "목동",
    "036": "영등포",
    "041": "동대문",
    "046": "은평",
    "049": "합정",
    "056": "청량리",
    "058": "가든파이브",
    "068": "수유",
    "072": "서울대",
    "074": "이화여대",
    "090": "천호",
}

# __next_f.push payload에서 BookInfoInkPage props JSON을 추출하는 패턴
_NEXT_DATA_RE = re.compile(
    r'self\.__next_f\.push\(\[1,"8:(.*?)"\]\)</script>',
    re.DOTALL,
)


def _parse_kiosk_html(html: str) -> tuple[int, str | None, str | None]:
    """Parse kiosk HTML to extract inventory quantity, location, and store tel.

    Returns (quantity, location_str, tel).
    """
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return 0, None, None

    try:
        raw = match.group(1)
        # The payload is a JS string literal (double-escaped JSON).
        # Decode the JS string escapes first, then parse as JSON.
        decoded = json.loads('"' + raw + '"')
        data = json.loads(decoded)

        # data is a JSON-RPC-like array: ["$", "ComponentName", null, {props}]
        props = data[3] if isinstance(data, list) and len(data) > 3 else data

        # Extract inventory
        inv_data = props.get("kbCommodityInventoryData", {})
        quantity = (
            inv_data.get("data", {}).get("inventory", {}).get("realInvnQntt", 0)
        )

        # Extract shelf location
        shelf_data = props.get("bookShelfData", {})
        shelf_infos = shelf_data.get("data", {}).get("bookShelfInfos", [])
        location = None
        if shelf_infos:
            info = shelf_infos[0]
            parts = [
                info.get("pavilion", ""),
                info.get("bkshNum", ""),
                info.get("bkshNm", ""),
            ]
            location = " ".join(p for p in parts if p)

        # Extract tel
        tel_data = props.get("storeInfoTelData", {})
        tel = tel_data.get("data", {}).get("storeTel", {}).get("storeTelNum")

        return quantity, location, tel
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return 0, None, None


class KyoboProvider(BaseProvider):
    provider_name = "kyobo"
    display_name = "교보문고"

    async def search_by_isbn(self, isbn13: str) -> ProviderResult:
        cache_key = f"kyobo:{isbn13}"
        if cache_key in inventory_cache:
            return inventory_cache[cache_key]

        try:
            tasks = [
                self._check_store(isbn13, code, name)
                for code, name in STORES.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            stores = [r for r in results if isinstance(r, StoreStock) and r.has_stock]

            result = ProviderResult(
                provider=self.provider_name,
                display_name=self.display_name,
                status="success",
                stores=stores,
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

    async def _check_store(
        self, isbn13: str, store_code: str, store_name: str
    ) -> StoreStock:
        resp = await self.client.get(
            KIOSK_URL,
            params={"site": store_code, "barcode": isbn13, "ejkGb": "KOR"},
            timeout=5.0,
        )
        resp.raise_for_status()

        quantity, location, _tel = _parse_kiosk_html(resp.text)

        return StoreStock(
            store_name=f"교보문고 {store_name}점",
            has_stock=quantity > 0,
            quantity=quantity,
            location=location,
        )
