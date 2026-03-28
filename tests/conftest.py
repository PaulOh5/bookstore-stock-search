import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings

# Set dummy API keys for testing
settings.kakao_api_key = "test_kakao_key"
settings.aladin_ttb_key = "test_aladin_key"

from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
