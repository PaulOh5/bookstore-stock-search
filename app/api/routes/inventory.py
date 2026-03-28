from fastapi import APIRouter, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.inventory import AggregatedInventory

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/inventory/{isbn13}", response_model=AggregatedInventory)
@limiter.limit("30/minute")
async def get_inventory(
    request: Request,
    isbn13: str = Path(..., pattern=r"^\d{13}$", description="ISBN-13"),
) -> AggregatedInventory:
    aggregator = request.app.state.aggregator
    return await aggregator.check_all(isbn13)
