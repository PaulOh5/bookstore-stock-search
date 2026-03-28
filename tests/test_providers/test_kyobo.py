import pytest
import respx
from httpx import AsyncClient, Response

from app.cache.memory import inventory_cache
from app.providers.kyobo import KyoboProvider, _parse_kiosk_html

# A minimal kiosk HTML response with inventory data embedded
KIOSK_HTML_WITH_STOCK = """
<!DOCTYPE html><html lang="ko"><head></head><body>
<script>self.__next_f=self.__next_f||[]</script>
<script>self.__next_f.push([1,"8:[\\"$\\",\\"$L19\\",null,{\\"site\\":\\"001\\",\\"barcode\\":\\"9788932917245\\",\\"bookShelfData\\":{\\"data\\":{\\"bookShelfInfos\\":[{\\"pavilion\\":\\"J관\\",\\"bkshNm\\":\\"세계문학\\",\\"bkshNum\\":\\"19-1\\",\\"bkshDvsnNm\\":\\"서가\\"}]},\\"statusCode\\":200},\\"kbCommodityInventoryData\\":{\\"data\\":{\\"inventory\\":{\\"realInvnQntt\\":3}},\\"statusCode\\":200},\\"storeInfoTelData\\":{\\"data\\":{\\"storeTel\\":{\\"rdpCode\\":\\"001\\",\\"storeNm\\":\\"광화문점\\",\\"storeTelNum\\":\\"(02)397-3416~7\\"}},\\"statusCode\\":200}}]"])</script>
</body></html>
"""

KIOSK_HTML_NO_STOCK = """
<!DOCTYPE html><html lang="ko"><head></head><body>
<script>self.__next_f=self.__next_f||[]</script>
<script>self.__next_f.push([1,"8:[\\"$\\",\\"$L19\\",null,{\\"site\\":\\"015\\",\\"barcode\\":\\"0000000000000\\",\\"bookShelfData\\":{\\"data\\":{\\"bookShelfInfos\\":[]},\\"statusCode\\":200},\\"kbCommodityInventoryData\\":{\\"data\\":{\\"inventory\\":{\\"realInvnQntt\\":0}},\\"statusCode\\":200},\\"storeInfoTelData\\":{\\"data\\":{\\"storeTel\\":{\\"rdpCode\\":\\"015\\",\\"storeNm\\":\\"강남점\\",\\"storeTelNum\\":\\"(02)1234-5678\\"}},\\"statusCode\\":200}}]"])</script>
</body></html>
"""


@pytest.fixture(autouse=True)
def clear_cache():
    inventory_cache.clear()
    yield
    inventory_cache.clear()


class TestParseKioskHtml:
    def test_with_stock(self):
        quantity, location, tel = _parse_kiosk_html(KIOSK_HTML_WITH_STOCK)
        assert quantity == 3
        assert location == "J관 19-1 세계문학"
        assert tel == "(02)397-3416~7"

    def test_no_stock(self):
        quantity, location, tel = _parse_kiosk_html(KIOSK_HTML_NO_STOCK)
        assert quantity == 0
        assert location is None
        assert tel is not None

    def test_invalid_html(self):
        quantity, location, tel = _parse_kiosk_html("<html></html>")
        assert quantity == 0
        assert location is None
        assert tel is None


@pytest.mark.asyncio
@respx.mock
async def test_kyobo_finds_stock():
    # Mock all store requests - only store 001 has stock
    respx.get("https://kiosk.kyobobook.co.kr/bookInfoInk").mock(
        side_effect=lambda request: (
            Response(200, text=KIOSK_HTML_WITH_STOCK)
            if request.url.params.get("site") == "001"
            else Response(200, text=KIOSK_HTML_NO_STOCK)
        )
    )

    async with AsyncClient() as client:
        provider = KyoboProvider(client)
        result = await provider.search_by_isbn("9788932917245")

    assert result.status == "success"
    assert len(result.stores) == 1
    assert result.stores[0].store_name == "교보문고 광화문점"
    assert result.stores[0].quantity == 3
    assert result.stores[0].location == "J관 19-1 세계문학"


@pytest.mark.asyncio
@respx.mock
async def test_kyobo_no_stock_anywhere():
    respx.get("https://kiosk.kyobobook.co.kr/bookInfoInk").mock(
        return_value=Response(200, text=KIOSK_HTML_NO_STOCK)
    )

    async with AsyncClient() as client:
        provider = KyoboProvider(client)
        result = await provider.search_by_isbn("0000000000000")

    assert result.status == "success"
    assert len(result.stores) == 0


@pytest.mark.asyncio
@respx.mock
async def test_kyobo_partial_failure():
    call_count = 0

    def mock_handler(request):
        nonlocal call_count
        call_count += 1
        if request.url.params.get("site") == "001":
            return Response(200, text=KIOSK_HTML_WITH_STOCK)
        if request.url.params.get("site") == "015":
            return Response(500)
        return Response(200, text=KIOSK_HTML_NO_STOCK)

    respx.get("https://kiosk.kyobobook.co.kr/bookInfoInk").mock(
        side_effect=mock_handler
    )

    async with AsyncClient() as client:
        provider = KyoboProvider(client)
        result = await provider.search_by_isbn("9788932917245")

    # Should still succeed with partial results (store 001 has stock)
    assert result.status == "success"
    assert len(result.stores) == 1
    assert result.stores[0].store_name == "교보문고 광화문점"
