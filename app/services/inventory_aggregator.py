import asyncio

from app.config import settings
from app.models.inventory import AggregatedInventory, ProviderResult
from app.providers.base import BaseProvider


class InventoryAggregator:
    def __init__(self, providers: list[BaseProvider]) -> None:
        self.providers = providers
        self.timeout = settings.provider_timeout

    async def check_all(self, isbn13: str) -> AggregatedInventory:
        tasks = [
            asyncio.wait_for(p.search_by_isbn(isbn13), timeout=self.timeout)
            for p in self.providers
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[ProviderResult] = []
        for provider, raw in zip(self.providers, raw_results):
            if isinstance(raw, asyncio.TimeoutError):
                results.append(
                    ProviderResult(
                        provider=provider.provider_name,
                        display_name=provider.display_name,
                        status="timeout",
                        error_message=f"{self.timeout}초 타임아웃",
                    )
                )
            elif isinstance(raw, Exception):
                results.append(
                    ProviderResult(
                        provider=provider.provider_name,
                        display_name=provider.display_name,
                        status="error",
                        error_message=str(raw),
                    )
                )
            else:
                results.append(raw)

        total = sum(
            len([s for s in r.stores if s.has_stock])
            for r in results
            if r.status == "success"
        )

        return AggregatedInventory(
            isbn13=isbn13,
            results=results,
            total_stores_with_stock=total,
        )
