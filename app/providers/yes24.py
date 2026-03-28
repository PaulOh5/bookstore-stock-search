from app.models.inventory import ProviderResult
from app.providers.base import BaseProvider


class Yes24Provider(BaseProvider):
    provider_name = "yes24"
    display_name = "YES24"

    async def search_by_isbn(self, isbn13: str) -> ProviderResult:
        # TODO: Phase 2 - YES24 매장 재고 스크래핑 구현
        return ProviderResult(
            provider=self.provider_name,
            display_name=self.display_name,
            status="error",
            error_message="아직 구현되지 않았습니다",
        )
