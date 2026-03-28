from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/health")
async def health(request: Request) -> dict:
    providers = request.app.state.aggregator.providers
    return {
        "status": "ok",
        "providers": [
            {"name": p.provider_name, "display_name": p.display_name}
            for p in providers
        ],
    }
