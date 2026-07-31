"""
Postgres 持久化包对外入口

文件职责
--------
对外只暴露启动 / 关闭函数；真正建池、装 Checkpointer、挂 Session/Trace/Audit
的逻辑在 ``bootstrap.py``，表结构 DDL 在 ``schema.py``。

白话概念
--------
「持久化」= 对话状态、会话列表、Trace、审计能不能重启后还在。
有 POSTGRES_DSN 用数据库；没有则用内存（开发方便，重启清空）。

在 Agent 流程中的位置
--------------------
  app.main lifespan
    → init_persistence(...)  # 启动
    → close_persistence()    # 关闭

如何被调用
----------
  from app.persistence import init_persistence, close_persistence
"""

# 从 bootstrap re-export 启动/关闭函数，供 app.main 等调用
from app.persistence.bootstrap import close_persistence, init_persistence

# __all__ 限定 from app.persistence import * 时导出的名称
__all__ = ["init_persistence", "close_persistence"]
