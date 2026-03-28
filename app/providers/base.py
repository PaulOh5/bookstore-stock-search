from abc import ABC, abstractmethod

import httpx

from app.models.inventory import ProviderResult


class BaseProvider(ABC):
    provider_name: str
    display_name: str

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    @abstractmethod
    async def search_by_isbn(self, isbn13: str) -> ProviderResult: ...
