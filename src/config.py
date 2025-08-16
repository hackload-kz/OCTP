import enum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import AliasChoices
from pydantic import Field
from pydantic import PostgresDsn
from pydantic import RedisDsn
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Environment(enum.StrEnum):
    DEV = "dev"
    PROD = "prod"


class AppSettings:
    """Basic settings for the application."""

    APP_NAME: str = "octofy"
    VERSION: str = Field("0.1.0", alias="TAG")

    ENV: Environment | None = None
    DEBUG: bool = False
    WEB_BASE_URL: str
    SITE_URL: str = "http://localhost:8000"
    TIMEZONE: str = "Asia/Almaty"

    ALLOWED_HOSTS: list[str] = Field(default=["*"])
    CORS_ALLOW_ORIGINS: list[str] = Field(default=["*"])
    CORS_ALLOW_METHODS: list[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default=["*"])
    CORS_EXPOSE_HEADERS: list[str] = Field(default=["*"])
    CONTENT_MAX_LENGTH: int = 50 * 1024 * 1024  # 50 MB

    # Thread pool size for sync/blocking IO requests
    THREAD_POOL_SIZE: int = 10


class AuthSettings:
    """Settings for the basic authentication."""

    SECRET_KEY: str
    PASSWORD_HASHERS: tuple[str] = ("bcrypt",)


class RedisSettings:
    """Settings for the Redis."""

    REDIS_SCHEME: str | None = "redis"
    REDIS_USER: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: str = "0"

    REDIS_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "CACHE_URL"),
    )

    @model_validator(mode="after")
    def validate_redis_url(self) -> Self:
        if self.REDIS_URL:
            redis_dsn = RedisDsn(self.REDIS_URL)
            self.REDIS_SCHEME = redis_dsn.scheme
            self.REDIS_USER = redis_dsn.username
            self.REDIS_PASSWORD = redis_dsn.password
            self.REDIS_HOST = redis_dsn.host
            self.REDIS_PORT = redis_dsn.port
            self.REDIS_DB = redis_dsn.path.strip("/")
        else:
            redis_dsn = RedisDsn.build(
                scheme=self.REDIS_SCHEME,
                username=self.REDIS_USER,
                password=self.REDIS_PASSWORD,
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                path=self.REDIS_DB,
            )
            self.REDIS_URL = redis_dsn.unicode_string()
        return self


#
#
# class AmqpSettings:
#     """Settings for the RabbitMQ."""
#
#     AMQP_SCHEME: str = "amqp"
#     AMQP_USER: str | None = None
#     AMQP_PASSWORD: str | None = None
#     AMQP_HOST: str | None = "localhost"
#     AMQP_PORT: int | None = 5672
#     AMQP_VHOST: str | None = None
#
#     AMQP_URL: str | None = Field(
#         default=None,
#         validation_alias=AliasChoices("RABBIT_URL", "AMQP_URL"),
#     )
#
#     @model_validator(mode="after")
#     def validate_amqp_url(self) -> Self:
#         if self.AMQP_URL:
#             amqp_dsn = AmqpDsn(self.AMQP_URL)
#             self.AMQP_SCHEME = amqp_dsn.scheme
#             self.AMQP_USER = amqp_dsn.username
#             self.AMQP_PASSWORD = amqp_dsn.password
#             self.AMQP_HOST = amqp_dsn.host
#             self.AMQP_PORT = amqp_dsn.port
#             self.AMQP_VHOST = amqp_dsn.path
#         else:
#             amqp_dsn = AmqpDsn.build(
#                 scheme=self.AMQP_SCHEME,
#                 username=self.AMQP_USER,
#                 password=self.AMQP_PASSWORD,
#                 host=self.AMQP_HOST,
#                 port=self.AMQP_PORT,
#                 path=self.AMQP_VHOST,
#             )
#             self.AMQP_URL = amqp_dsn.unicode_string()
#         return self


class PostgresSettings:
    """Settings for the PostgreSQL."""

    POSTGRES_SCHEME: str = "postgresql+psycopg"
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_HOST: str | None = "localhost"
    POSTGRES_PORT: int | None = 5432
    POSTGRES_DB: str | None = None

    POSTGRES_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("POSTGRES_URL", "DATABASE_URL"),
    )

    # Database connection pool settings
    DB_POOL_SIZE: int = 5
    DB_POOL_TTL: int = 60 * 20  # 20 minutes
    DB_POOL_PRE_PING: bool = True
    # Use pgBouncer for connection pooling
    USE_PGBOUNCER: bool = False

    @model_validator(mode="after")
    def validate_postgres_url(self) -> Self:
        if self.POSTGRES_URL:
            postgres_dsn = PostgresDsn(self.POSTGRES_URL)
            host = postgres_dsn.hosts()[0]
            self.POSTGRES_SCHEME = postgres_dsn.scheme
            self.POSTGRES_USER = host["username"]
            self.POSTGRES_PASSWORD = host["password"]
            self.POSTGRES_HOST = host["host"]
            self.POSTGRES_PORT = host["port"]
            self.POSTGRES_DB = postgres_dsn.path.strip("/")
        else:
            postgres_dsn = PostgresDsn.build(
                scheme=self.POSTGRES_SCHEME,
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
            self.POSTGRES_URL = postgres_dsn.unicode_string()
        return self


class Settings(
    BaseSettings,
    AppSettings,
    AuthSettings,
    RedisSettings,
    PostgresSettings,
):
    """Project settings."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / ".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
