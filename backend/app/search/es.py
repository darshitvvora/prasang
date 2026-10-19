from elasticsearch import AsyncElasticsearch

from app.config import get_settings


def get_es() -> AsyncElasticsearch:
    return AsyncElasticsearch(get_settings().elasticsearch_url, request_timeout=5)


def alias() -> str:
    return get_settings().es_alias
