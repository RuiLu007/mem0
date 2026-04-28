"""
Vector store strategy pattern for OpenMemory.

Design
------
VectorStoreBase is an abstract base class (Strategy interface).
Each concrete class encapsulates one backend's configuration logic and returns
a mem0-compatible config dict via ``get_mem0_config()``.

``detect_vector_store()`` is the factory that auto-selects the right strategy
from environment variables (FAISS is the default when nothing else is set).

Adding a new backend
--------------------
1. Subclass ``VectorStoreBase``.
2. Implement ``provider_name`` property and ``get_mem0_config()`` method.
3. Add detection logic to ``detect_vector_store()`` (or register it in
   ``_REGISTRY`` if the backend has a simple single-env-var trigger).

Current supported backends
--------------------------
  faiss        → local, no extra service needed  (DEFAULT)
  qdrant       → requires QDRANT_HOST + QDRANT_PORT
  milvus       → requires MILVUS_HOST + MILVUS_PORT
  chroma       → requires CHROMA_HOST + CHROMA_PORT
  pgvector     → requires PG_HOST + PG_PORT
  redis        → requires REDIS_URL
  weaviate     → requires WEAVIATE_CLUSTER_URL or WEAVIATE_HOST+PORT
  elasticsearch→ requires ELASTICSEARCH_HOST + ELASTICSEARCH_PORT
  opensearch   → requires OPENSEARCH_HOST + OPENSEARCH_PORT
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base (Strategy interface)
# ─────────────────────────────────────────────────────────────────────────────

class VectorStoreBase(ABC):
    """Abstract strategy for building a mem0 vector-store configuration."""

    COLLECTION = "openmemory"
    DEFAULT_DIMS = 1536

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """mem0 provider name string."""

    @abstractmethod
    def get_mem0_config(self) -> dict:
        """Return a ready-to-use mem0 vector_store section dict."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider_name}>"


# ─────────────────────────────────────────────────────────────────────────────
# FAISS  (default / primary backend)
# ─────────────────────────────────────────────────────────────────────────────

class FaissVectorStore(VectorStoreBase):
    """
    Local FAISS vector store.

    Persistence
    -----------
    mem0 serialises the FAISS index and a metadata JSON file under ``path/``.
    On first run the directory is created automatically; on subsequent runs the
    existing index is loaded from disk, so no data is lost across restarts.

    Relevant files written by mem0:
      {path}/index.faiss   – binary FAISS index
      {path}/index.pkl     – id → metadata mapping

    Environment variables
    ---------------------
    FAISS_PATH            Path to the persistence directory (required to
                          activate this backend; defaults to ./faiss_store)
    FAISS_DIMS            Embedding dimensionality (default: 1536)
    FAISS_DISTANCE        Distance metric: cosine | l2 | ip  (default: cosine)
    """

    def __init__(
        self,
        path: Optional[str] = None,
        collection_name: str = VectorStoreBase.COLLECTION,
        embedding_dims: Optional[int] = None,
        distance_strategy: str = "cosine",
    ):
        self.path = path or os.environ.get("FAISS_PATH", "./faiss_store")
        self.collection_name = collection_name
        self.embedding_dims = embedding_dims or int(
            os.environ.get("FAISS_DIMS", VectorStoreBase.DEFAULT_DIMS)
        )
        self.distance_strategy = (
            os.environ.get("FAISS_DISTANCE", distance_strategy).lower()
        )

    @property
    def provider_name(self) -> str:
        return "faiss"

    def get_mem0_config(self) -> dict:
        # Ensure persistence directory exists so mem0 can write immediately
        os.makedirs(self.path, exist_ok=True)
        return {
            "provider": "faiss",
            "config": {
                "collection_name": self.collection_name,
                "path": self.path,
                "embedding_model_dims": self.embedding_dims,
                "distance_strategy": self.distance_strategy,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Qdrant
# ─────────────────────────────────────────────────────────────────────────────

class QdrantVectorStore(VectorStoreBase):
    """
    Qdrant vector store.

    Environment variables
    ---------------------
    QDRANT_HOST    hostname (required)
    QDRANT_PORT    port (required)
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.environ.get("QDRANT_HOST", "localhost")
        self.port = port or int(os.environ.get("QDRANT_PORT", 6333))

    @property
    def provider_name(self) -> str:
        return "qdrant"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "qdrant",
            "config": {
                "collection_name": self.COLLECTION,
                "host": self.host,
                "port": self.port,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Milvus  (stub – ready for future migration)
# ─────────────────────────────────────────────────────────────────────────────

class MilvusVectorStore(VectorStoreBase):
    """
    Milvus / Zilliz vector store.

    Environment variables
    ---------------------
    MILVUS_HOST        hostname (required)
    MILVUS_PORT        port (required)
    MILVUS_TOKEN       auth token (optional, empty for local)
    MILVUS_DB_NAME     database name (optional)
    MILVUS_DIMS        embedding dims (default: 1536)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        token: Optional[str] = None,
        db_name: Optional[str] = None,
        embedding_dims: Optional[int] = None,
    ):
        self.host = host or os.environ.get("MILVUS_HOST", "localhost")
        self.port = port or int(os.environ.get("MILVUS_PORT", 19530))
        self.token = token if token is not None else os.environ.get("MILVUS_TOKEN", "")
        self.db_name = db_name or os.environ.get("MILVUS_DB_NAME", "")
        self.embedding_dims = embedding_dims or int(
            os.environ.get("MILVUS_DIMS", self.DEFAULT_DIMS)
        )

    @property
    def provider_name(self) -> str:
        return "milvus"

    def get_mem0_config(self) -> dict:
        url = f"http://{self.host}:{self.port}"
        return {
            "provider": "milvus",
            "config": {
                "collection_name": self.COLLECTION,
                "url": url,
                "token": self.token,
                "db_name": self.db_name,
                "embedding_model_dims": self.embedding_dims,
                "metric_type": "COSINE",
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Chroma
# ─────────────────────────────────────────────────────────────────────────────

class ChromaVectorStore(VectorStoreBase):
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.environ.get("CHROMA_HOST", "localhost")
        self.port = port or int(os.environ.get("CHROMA_PORT", 8000))

    @property
    def provider_name(self) -> str:
        return "chroma"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "chroma",
            "config": {
                "collection_name": self.COLLECTION,
                "host": self.host,
                "port": self.port,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# pgvector
# ─────────────────────────────────────────────────────────────────────────────

class PgVectorStore(VectorStoreBase):
    def __init__(self):
        self.host = os.environ.get("PG_HOST", "localhost")
        self.port = int(os.environ.get("PG_PORT", 5432))
        self.dbname = os.environ.get("PG_DB", "mem0")
        self.user = os.environ.get("PG_USER", "mem0")
        self.password = os.environ.get("PG_PASSWORD", "mem0")

    @property
    def provider_name(self) -> str:
        return "pgvector"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "pgvector",
            "config": {
                "collection_name": self.COLLECTION,
                "host": self.host,
                "port": self.port,
                "dbname": self.dbname,
                "user": self.user,
                "password": self.password,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Redis
# ─────────────────────────────────────────────────────────────────────────────

class RedisVectorStore(VectorStoreBase):
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")

    @property
    def provider_name(self) -> str:
        return "redis"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "redis",
            "config": {
                "collection_name": self.COLLECTION,
                "redis_url": self.redis_url,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Weaviate
# ─────────────────────────────────────────────────────────────────────────────

class WeaviateVectorStore(VectorStoreBase):
    def __init__(self, cluster_url: Optional[str] = None):
        self.cluster_url = cluster_url or os.environ.get("WEAVIATE_CLUSTER_URL")
        if not self.cluster_url:
            host = os.environ.get("WEAVIATE_HOST", "localhost")
            port = int(os.environ.get("WEAVIATE_PORT", 8080))
            self.cluster_url = f"http://{host}:{port}"

    @property
    def provider_name(self) -> str:
        return "weaviate"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "weaviate",
            "config": {
                "collection_name": self.COLLECTION,
                "cluster_url": self.cluster_url,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Elasticsearch
# ─────────────────────────────────────────────────────────────────────────────

class ElasticsearchVectorStore(VectorStoreBase):
    def __init__(self):
        host = os.environ.get("ELASTICSEARCH_HOST", "localhost")
        self.host = f"http://{host}"
        self.port = int(os.environ.get("ELASTICSEARCH_PORT", 9200))
        self.user = os.environ.get("ELASTICSEARCH_USER", "elastic")
        self.password = os.environ.get("ELASTICSEARCH_PASSWORD", "changeme")

    @property
    def provider_name(self) -> str:
        return "elasticsearch"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "elasticsearch",
            "config": {
                "collection_name": self.COLLECTION,
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "verify_certs": False,
                "use_ssl": False,
                "embedding_model_dims": self.DEFAULT_DIMS,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# OpenSearch
# ─────────────────────────────────────────────────────────────────────────────

class OpenSearchVectorStore(VectorStoreBase):
    def __init__(self):
        self.host = os.environ.get("OPENSEARCH_HOST", "localhost")
        self.port = int(os.environ.get("OPENSEARCH_PORT", 9200))

    @property
    def provider_name(self) -> str:
        return "opensearch"

    def get_mem0_config(self) -> dict:
        return {
            "provider": "opensearch",
            "config": {
                "collection_name": self.COLLECTION,
                "host": self.host,
                "port": self.port,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Factory  — auto-detect from environment variables
# ─────────────────────────────────────────────────────────────────────────────

def detect_vector_store() -> VectorStoreBase:
    """
    Auto-select a vector store strategy based on environment variables.

    Detection priority (first match wins):
      1. Chroma       CHROMA_HOST + CHROMA_PORT
      2. Qdrant       QDRANT_HOST + QDRANT_PORT
      3. Weaviate     WEAVIATE_CLUSTER_URL  or  WEAVIATE_HOST + WEAVIATE_PORT
      4. Redis        REDIS_URL
      5. pgvector     PG_HOST + PG_PORT
      6. Milvus       MILVUS_HOST + MILVUS_PORT
      7. Elasticsearch ELASTICSEARCH_HOST + ELASTICSEARCH_PORT
      8. OpenSearch   OPENSEARCH_HOST + OPENSEARCH_PORT
      9. FAISS        FAISS_PATH  (or no env var at all → default)

    Override with VECTOR_STORE env var to force a specific backend.
    """
    override = os.environ.get("VECTOR_STORE", "").lower()
    if override:
        _map = {
            "faiss": FaissVectorStore,
            "qdrant": QdrantVectorStore,
            "milvus": MilvusVectorStore,
            "chroma": ChromaVectorStore,
            "pgvector": PgVectorStore,
            "redis": RedisVectorStore,
            "weaviate": WeaviateVectorStore,
            "elasticsearch": ElasticsearchVectorStore,
            "opensearch": OpenSearchVectorStore,
        }
        cls = _map.get(override)
        if cls:
            return cls()
        raise ValueError(
            f"VECTOR_STORE='{override}' is not supported. "
            f"Choose one of: {', '.join(_map)}"
        )

    # Auto-detect
    if os.environ.get("CHROMA_HOST") and os.environ.get("CHROMA_PORT"):
        return ChromaVectorStore()
    if os.environ.get("QDRANT_HOST") and os.environ.get("QDRANT_PORT"):
        return QdrantVectorStore()
    if os.environ.get("WEAVIATE_CLUSTER_URL") or (
        os.environ.get("WEAVIATE_HOST") and os.environ.get("WEAVIATE_PORT")
    ):
        return WeaviateVectorStore()
    if os.environ.get("REDIS_URL"):
        return RedisVectorStore()
    if os.environ.get("PG_HOST") and os.environ.get("PG_PORT"):
        return PgVectorStore()
    if os.environ.get("MILVUS_HOST") and os.environ.get("MILVUS_PORT"):
        return MilvusVectorStore()
    if os.environ.get("ELASTICSEARCH_HOST") and os.environ.get("ELASTICSEARCH_PORT"):
        return ElasticsearchVectorStore()
    if os.environ.get("OPENSEARCH_HOST") and os.environ.get("OPENSEARCH_PORT"):
        return OpenSearchVectorStore()

    # Default: FAISS (works with or without FAISS_PATH)
    return FaissVectorStore()
