import pytest
import respx
from httpx import AsyncClient, Response

from app.cache.memory import inventory_cache
from app.providers.youngpoong import YoungpoongProvider

GUEST_LOGIN_RESPONSE = {
    "state": "SUCCESS",
    "stateCode": 200,
    "data": {"accessToken": "test_token_abc", "refreshToken": "test_refresh"},
}

SEARCH_RESPONSE_FOUND = {
    "state": "SUCCESS",
    "data": {
        "ypProductResult": {
            "totalCount": 1,
            "dataList": [
                {
                    "bookCd": "101154898",
                    "productName": "삼체 1부 : 삼체문제",
                    "productIdCd": "9788954442695",
                    "productPrice": "17000",
                }
            ],
        }
    },
}

SEARCH_RESPONSE_EMPTY = {
    "state": "SUCCESS",
    "data": {"ypProductResult": {"totalCount": 0, "dataList": []}},
}

STOCK_RESPONSE = {
    "state": "SUCCESS",
    "data": [
        {"werks": "4900", "werksNm": "가산마리오", "labst": 5},
        {"werks": "6450", "werksNm": "강남롯데", "labst": 2},
        {"werks": "2000", "werksNm": "종로", "labst": 0},
        {"werks": "5800", "werksNm": "김포공항롯데", "labst": 0},
    ],
}


@pytest.fixture(autouse=True)
def clear_cache():
    inventory_cache.clear()
    yield
    inventory_cache.clear()


@pytest.mark.asyncio
@respx.mock
async def test_youngpoong_full_flow():
    respx.put("https://www.ypbooks.co.kr/back_login/base_login/api/v1/auth/login-guest").mock(
        return_value=Response(200, json=GUEST_LOGIN_RESPONSE)
    )
    respx.get("https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/search_indexes/result/product").mock(
        return_value=Response(200, json=SEARCH_RESPONSE_FOUND)
    )
    respx.get("https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/product/stock-info").mock(
        return_value=Response(200, json=STOCK_RESPONSE)
    )

    async with AsyncClient() as client:
        provider = YoungpoongProvider(client)
        result = await provider.search_by_isbn("9788954442695")

    assert result.status == "success"
    assert len(result.stores) == 2
    assert result.stores[0].store_name == "영풍문고 가산마리오"
    assert result.stores[0].quantity == 5
    assert result.stores[1].store_name == "영풍문고 강남롯데"
    assert result.stores[1].quantity == 2


@pytest.mark.asyncio
@respx.mock
async def test_youngpoong_book_not_found():
    respx.put("https://www.ypbooks.co.kr/back_login/base_login/api/v1/auth/login-guest").mock(
        return_value=Response(200, json=GUEST_LOGIN_RESPONSE)
    )
    respx.get("https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/search_indexes/result/product").mock(
        return_value=Response(200, json=SEARCH_RESPONSE_EMPTY)
    )

    async with AsyncClient() as client:
        provider = YoungpoongProvider(client)
        result = await provider.search_by_isbn("0000000000000")

    assert result.status == "success"
    assert len(result.stores) == 0


@pytest.mark.asyncio
@respx.mock
async def test_youngpoong_guest_login_failure():
    respx.put("https://www.ypbooks.co.kr/back_login/base_login/api/v1/auth/login-guest").mock(
        return_value=Response(200, json={"state": "FAIL", "msg": "System error", "data": None})
    )

    async with AsyncClient() as client:
        provider = YoungpoongProvider(client)
        result = await provider.search_by_isbn("9788954442695")

    assert result.status == "error"
    assert "Guest login failed" in result.error_message


@pytest.mark.asyncio
@respx.mock
async def test_youngpoong_stock_api_error():
    respx.put("https://www.ypbooks.co.kr/back_login/base_login/api/v1/auth/login-guest").mock(
        return_value=Response(200, json=GUEST_LOGIN_RESPONSE)
    )
    respx.get("https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/search_indexes/result/product").mock(
        return_value=Response(200, json=SEARCH_RESPONSE_FOUND)
    )
    respx.get("https://www.ypbooks.co.kr/back_shop/base_shop/api/v1/product/stock-info").mock(
        return_value=Response(500)
    )

    async with AsyncClient() as client:
        provider = YoungpoongProvider(client)
        result = await provider.search_by_isbn("9788954442695")

    assert result.status == "error"
