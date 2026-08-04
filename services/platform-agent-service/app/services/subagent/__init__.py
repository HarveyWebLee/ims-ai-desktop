"""轻量 Subagent：知识检索子任务（摘要回主 agent，无 checkpointer）。"""

from app.services.subagent.knowledge_research import research_knowledge

__all__ = ["research_knowledge"]
