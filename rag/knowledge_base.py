from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import uuid
from typing import Iterable

from config.settings import settings

try:  # pragma: no cover - optional dependency
    import faiss  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    faiss = None

try:  # pragma: no cover - optional dependency
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None

try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    SentenceTransformer = None


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
DEFAULT_CORPUS_PATH = Path(__file__).with_name("legal_corpus.json")


@dataclass
class LegalDocument:
    id: str
    title: str
    citation: str
    content: str
    keywords: tuple[str, ...] = ()
    source: str = "built-in"
    score: float = field(default=0.0, compare=False)

    @property
    def text(self) -> str:
        keyword_text = f" Keywords: {', '.join(self.keywords)}." if self.keywords else ""
        return f"{self.title}. Citation: {self.citation}. {self.content}{keyword_text}"


class LocalVectorIndex:
    """
    Lightweight semantic-ish fallback when FAISS/embeddings are unavailable.

    It uses normalized token frequencies with IDF weighting so retrieval remains
    contextual instead of relying on a single hardcoded keyword match.
    """

    def __init__(self, documents: list[LegalDocument]):
        self.documents = documents
        self.doc_tokens = [self._tokenize(doc.text) for doc in documents]
        self.idf = self._build_idf(self.doc_tokens)
        self.doc_vectors = [self._vectorize(tokens) for tokens in self.doc_tokens]

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        query_tokens = self._tokenize(query)
        query_vector = self._vectorize(query_tokens)
        if not query_vector:
            return [(index, 0.0) for index in range(min(limit, len(self.documents)))]

        scored: list[tuple[int, float]] = []
        for index, doc_vector in enumerate(self.doc_vectors):
            score = self._cosine_similarity(query_vector, doc_vector)
            if score > 0:
                scored.append((index, score))

        if not scored:
            scored = [(index, 0.0) for index in range(len(self.documents))]

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return TOKEN_PATTERN.findall(text.lower())

    @staticmethod
    def _build_idf(doc_tokens: list[list[str]]) -> dict[str, float]:
        total_docs = max(len(doc_tokens), 1)
        doc_freq: Counter[str] = Counter()
        for tokens in doc_tokens:
            doc_freq.update(set(tokens))
        return {
            token: math.log((1 + total_docs) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        term_freq = Counter(tokens)
        total = len(tokens)
        vector = {
            token: (count / total) * self.idf.get(token, 1.0)
            for token, count in term_freq.items()
        }
        magnitude = math.sqrt(sum(value * value for value in vector.values()))
        if magnitude == 0:
            return {}
        return {token: value / magnitude for token, value in vector.items()}

    @staticmethod
    def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
        shared = set(left).intersection(right)
        return sum(left[token] * right[token] for token in shared)


class SemanticVectorIndex:
    def __init__(self, documents: list[LegalDocument], model_name: str):
        if SentenceTransformer is None or faiss is None or np is None:
            raise RuntimeError("Semantic dependencies are unavailable")

        self.documents = documents
        self.model = SentenceTransformer(model_name, local_files_only=True)
        self.embeddings = self._encode([doc.text for doc in documents])
        dimension = int(self.embeddings.shape[1])
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embeddings)

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        query_embedding = self._encode([query])
        scores, indices = self.index.search(query_embedding, limit)
        return [
            (int(doc_index), float(score))
            for doc_index, score in zip(indices[0], scores[0])
            if int(doc_index) >= 0
        ]

    def _encode(self, texts: Iterable[str]):
        embeddings = self.model.encode(list(texts), normalize_embeddings=True)
        return np.asarray(embeddings, dtype="float32")


class LegalKnowledgeBase:
    def __init__(self, corpus_path: str | Path | None = None) -> None:
        self.corpus_path = Path(corpus_path) if corpus_path else DEFAULT_CORPUS_PATH
        self.documents = self._load_documents(self.corpus_path)
        self.backend = "local-vector"
        self._index = self._build_index()

    def retrieve(self, query: str, limit: int | None = None) -> list[LegalDocument]:
        matches = self._index.search(query, limit or settings.TOP_K_DOCS)
        results: list[LegalDocument] = []
        for doc_index, score in matches:
            source = self.documents[doc_index]
            results.append(
                LegalDocument(
                    id=source.id,
                    title=source.title,
                    citation=source.citation,
                    content=source.content,
                    keywords=source.keywords,
                    source=source.source,
                    score=score,
                )
            )
        return results

    def list_documents(self) -> list[dict[str, object]]:
        return [self._serialize_document(doc) for doc in self.documents]

    def upsert_document(self, payload: dict[str, object]) -> dict[str, object]:
        normalized = self._normalize_document_record(payload)
        existing_index = next(
            (index for index, doc in enumerate(self.documents) if doc.id == normalized["id"]),
            None,
        )
        document = LegalDocument(
            id=str(normalized["id"]),
            title=str(normalized["title"]),
            citation=str(normalized["citation"]),
            content=str(normalized["content"]),
            keywords=tuple(normalized["keywords"]),
            source=str(normalized["source"]),
        )
        if existing_index is None:
            self.documents.append(document)
        else:
            self.documents[existing_index] = document
        self._persist_documents()
        self.reload()
        return self._serialize_document(document)

    def delete_document(self, doc_id: str) -> bool:
        remaining = [doc for doc in self.documents if doc.id != doc_id]
        if len(remaining) == len(self.documents):
            return False
        self.documents = remaining
        self._persist_documents()
        self.reload()
        return True

    def reload(self) -> None:
        self.documents = self._load_documents(self.corpus_path)
        self.backend = "local-vector"
        self._index = self._build_index()

    def format_context(self, docs: list[LegalDocument]) -> str:
        chunks = []
        for doc in docs:
            lines = [
                f"Title: {doc.title}",
                f"Citation: {doc.citation}",
                f"Summary: {doc.content}",
            ]
            if doc.keywords:
                lines.append(f"Keywords: {', '.join(doc.keywords)}")
            if doc.score:
                lines.append(f"Relevance: {doc.score:.3f}")
            chunks.append("\n".join(lines))
        return "\n\n".join(chunks)

    def describe_backend(self) -> dict[str, str]:
        return {
            "backend": self.backend,
            "corpus_path": str(self.corpus_path),
            "documents": str(len(self.documents)),
        }

    def _build_index(self):
        if settings.ENABLE_SEMANTIC_RAG and SentenceTransformer and faiss and np:
            try:
                self.backend = f"faiss:{settings.EMBEDDING_MODEL}"
                return SemanticVectorIndex(self.documents, settings.EMBEDDING_MODEL)
            except Exception:
                self.backend = "local-vector"
        return LocalVectorIndex(self.documents)

    def _persist_documents(self) -> None:
        payload = [self._serialize_document(doc) for doc in self.documents]
        self.corpus_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _serialize_document(doc: LegalDocument) -> dict[str, object]:
        return {
            "id": doc.id,
            "title": doc.title,
            "citation": doc.citation,
            "content": doc.content,
            "keywords": list(doc.keywords),
            "source": doc.source,
        }

    @staticmethod
    def _normalize_document_record(payload: dict[str, object]) -> dict[str, object]:
        title = str(payload.get("title", "")).strip()
        citation = str(payload.get("citation", "")).strip()
        content = str(payload.get("content", "")).strip()
        source = str(payload.get("source", "legal_corpus.json")).strip() or "legal_corpus.json"
        keywords_raw = payload.get("keywords", [])
        if isinstance(keywords_raw, str):
            keywords = [item.strip() for item in keywords_raw.split(",") if item.strip()]
        else:
            keywords = [str(item).strip() for item in list(keywords_raw) if str(item).strip()]
        if not title or not citation or not content:
            raise ValueError("Title, citation, and content are required")
        return {
            "id": str(payload.get("id") or uuid.uuid4()),
            "title": title,
            "citation": citation,
            "content": content,
            "keywords": keywords,
            "source": source,
        }

    @staticmethod
    def _load_documents(path: Path) -> list[LegalDocument]:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [
                LegalDocument(
                    id=item.get("id") or str(uuid.uuid4()),
                    title=item["title"],
                    citation=item["citation"],
                    content=item["content"],
                    keywords=tuple(item.get("keywords", [])),
                    source=item.get("source", str(path.name)),
                )
                for item in payload
            ]
        raise FileNotFoundError(f"Legal corpus not found: {path}")
