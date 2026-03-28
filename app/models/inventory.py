from pydantic import BaseModel


class StoreStock(BaseModel):
    store_name: str
    has_stock: bool
    quantity: int | None = None
    price: str | None = None
    condition: str | None = None
    address: str | None = None
    location: str | None = None


class ProviderResult(BaseModel):
    provider: str
    display_name: str
    status: str  # "success" | "error" | "timeout"
    stores: list[StoreStock] = []
    error_message: str | None = None


class AggregatedInventory(BaseModel):
    isbn13: str
    results: list[ProviderResult]
    total_stores_with_stock: int
