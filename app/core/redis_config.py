import os
from arq.connections import RedisSettings


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from environment variables."""
    return RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        database=int(os.getenv("REDIS_DB", "0")),
    )


REDIS_SETTINGS = get_redis_settings()
