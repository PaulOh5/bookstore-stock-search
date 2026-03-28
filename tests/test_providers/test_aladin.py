import pytest
import respx
from httpx import AsyncClient, Response

from app.cache.memory import inventory_cache
from app.providers.aladin import AladinProvider


@pytest.fixture(autouse=True)
def clear_cache():
    inventory_cache.clear()
    yield
    inventory_cache.clear()


@pytest.mark.asyncio
@respx.mock
async def test_aladin_success():
    respx.get("http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx").mock(
        return_value=Response(200, json={
            "itemOffStoreList": [
                {"offCode": "GANGNAM", "offName": "알라딘 강남점", "offAddress": "서울 강남구"},
                {"offCode": "JONGNO", "offName": "알라딘 종로점", "offAddress": "서울 종로구"},
            ]
        })
    )

    async with AsyncClient() as client:
        provider = AladinProvider(client)
        result = await provider.search_by_isbn("9788983920997")

    assert result.status == "success"
    assert len(result.stores) == 2
    assert result.stores[0].store_name == "알라딘 강남점"
    assert result.stores[0].has_stock is True


@pytest.mark.asyncio
@respx.mock
async def test_aladin_empty():
    respx.get("http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx").mock(
        return_value=Response(200, json={"itemOffStoreList": []})
    )

    async with AsyncClient() as client:
        provider = AladinProvider(client)
        result = await provider.search_by_isbn("0000000000000")

    assert result.status == "success"
    assert len(result.stores) == 0


@pytest.mark.asyncio
@respx.mock
async def test_aladin_error():
    respx.get("http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx").mock(
        return_value=Response(500)
    )

    async with AsyncClient() as client:
        provider = AladinProvider(client)
        result = await provider.search_by_isbn("9788983920997")

    assert result.status == "error"
    assert result.error_message is not None
