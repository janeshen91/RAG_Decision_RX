from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.embeddings.factory import get_embedding_model
from app.embeddings.hash_embeddings import HashEmbeddingModel
from app.embeddings.openai_embeddings import OpenAIEmbeddingModel
from app.retrieval.vector_store import ChromaVectorStore


def test_factory_defaults_to_hash() -> None:
    embedder = get_embedding_model(Settings(embedding_provider="hash"))
    assert isinstance(embedder, HashEmbeddingModel)
    assert embedder.name == "hash-d384"
    assert embedder.dimension == 384


def test_factory_openai_requires_api_key() -> None:
    settings = Settings(embedding_provider="openai", openai_api_key=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_model(settings)


def test_factory_openai_selects_provider_without_calling_api() -> None:
    # A key is required, but constructing the client must not hit the network.
    settings = Settings(
        embedding_provider="openai",
        openai_api_key="sk-test-not-real",
        openai_embedding_model="text-embedding-3-small",
    )
    embedder = get_embedding_model(settings)
    assert isinstance(embedder, OpenAIEmbeddingModel)
    assert embedder.name == "openai-text-embedding-3-small"
    assert embedder.dimension == 1536  # known statically, no API call


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedding_model(Settings(embedding_provider="banana"))


def test_hash_embedding_roundtrip_dimensions() -> None:
    embedder = HashEmbeddingModel(dimensions=384)
    vectors = embedder.embed_texts(["alpha beta", "gamma"])
    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
    assert len(embedder.embed_query("alpha")) == 384


class _StubEmbedder:
    """Minimal EmbeddingModel for exercising vector-store namespacing/guards
    without any real embedding backend."""

    def __init__(self, name: str, dimension: int) -> None:
        self._name = name
        self._dimension = dimension

    @property
    def name(self) -> str:
        return self._name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self._dimension


def test_collection_is_namespaced_by_embedder(tmp_path: Path) -> None:
    settings = Settings(chroma_path=str(tmp_path / "chroma"), chroma_collection="decisionsrx")
    store = ChromaVectorStore(settings, HashEmbeddingModel(384))
    assert store.collection.name.startswith("decisionsrx__hash-d384")
    assert 3 <= len(store.collection.name) <= 63


def test_different_providers_use_different_collections(tmp_path: Path) -> None:
    settings = Settings(chroma_path=str(tmp_path / "chroma"), chroma_collection="decisionsrx")
    hash_store = ChromaVectorStore(settings, _StubEmbedder("hash-d384", 384))
    openai_store = ChromaVectorStore(settings, _StubEmbedder("openai-text-embedding-3-small", 1536))
    assert hash_store.collection.name != openai_store.collection.name


def test_same_dimension_different_embedder_stay_separate(tmp_path: Path) -> None:
    # Same dimension must not be enough to share a collection; the embedder
    # identity must keep them apart so providers can't silently mix.
    settings = Settings(chroma_path=str(tmp_path / "chroma"), chroma_collection="decisionsrx")
    a = ChromaVectorStore(settings, _StubEmbedder("provider-alpha", 384))
    b = ChromaVectorStore(settings, _StubEmbedder("provider-beta", 384))
    assert a.collection.name != b.collection.name


def test_long_collection_base_keeps_providers_separate(tmp_path: Path) -> None:
    # A long base must not truncate away provider separation, and names must
    # remain within Chroma's 3-63 char limit.
    long_base = "decisionsrx-" + "x" * 80
    settings = Settings(chroma_path=str(tmp_path / "chroma"), chroma_collection=long_base)
    a = ChromaVectorStore(settings, _StubEmbedder("provider-alpha", 384))
    b = ChromaVectorStore(settings, _StubEmbedder("provider-beta", 384))
    assert a.collection.name != b.collection.name
    for store in (a, b):
        assert 3 <= len(store.collection.name) <= 63


def test_dimension_mismatch_under_same_name_raises(tmp_path: Path) -> None:
    settings = Settings(chroma_path=str(tmp_path / "chroma"), chroma_collection="decisionsrx")
    # Build a collection at dimension 384, then reopen the same name at 1536.
    ChromaVectorStore(settings, _StubEmbedder("same-name", 384))
    with pytest.raises(ValueError, match="dimension"):
        ChromaVectorStore(settings, _StubEmbedder("same-name", 1536))
