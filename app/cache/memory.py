from cachetools import TTLCache

from app.config import settings

search_cache: TTLCache = TTLCache(maxsize=512, ttl=settings.search_cache_ttl)
inventory_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.inventory_cache_ttl)
