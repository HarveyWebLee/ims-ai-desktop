"""RAG 模块：对外再导出 store（物理实现仍在 infrastructure.vector，逐步迁入）。"""

from app.infrastructure.vector.store import SearchHit, VectorStoreService

__all__ = ["SearchHit", "VectorStoreService"]
