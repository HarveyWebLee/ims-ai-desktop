"""
可配置 Store 代理。

文件职责
--------
提供 ``StoreProxy``：模块级 ``xxx_store`` 始终指向同一代理对象；
启动时 ``configure`` 只替换内部 ``_inner``，避免「已 import 的模块仍握着旧实现」。

在 Agent 流程中的位置
--------------------
属于基础设施层；session_store / trace_store / audit_store 等均以此包装：
  进程启动 → bootstrap.configure_*_store(Postgres 或 Memory)
    → StoreProxy.configure(_inner)
  业务代码 → session_store.list_sessions(...) 等（经 __getattr__ 转发）

如何被调用
----------
- 各 ``*_store.py`` 模块底部：``xxx_store = StoreProxy(InMemory...)``
- ``persistence.bootstrap``：``configure_xxx_store(Postgres...)`` → ``proxy.configure``

白话解释
--------
想像大家手里都握着同一把「遥控器」（代理）。换电池（换成 Postgres 实现）时，
只换遥控器里面的芯片，不把遥控器重新发一把——否则有人还拿着旧遥控器往内存写，
有人往 Postgres 写，就会外键对不上。

问题背景（技术）
----------------
各 API 模块在 import 时执行 ``from app.services.xxx_store import xxx_store``，
得到的是当时绑定对象的引用。startup 中若 ``global xxx_store; xxx_store = new``，
已 import 的模块仍持有旧 InMemory，导致会话写内存而 pending/trace 写 Postgres。
"""

from __future__ import annotations

from typing import Any


class StoreProxy[T]:
    """
    将方法调用转发到当前配置的 Store 实例。

    属性:
        _inner: 真正的 InMemory / Postgres Store
    """

    def __init__(self, initial: T) -> None:
        """用初始实现（通常是内存 Store）构造代理。"""
        self._inner: T = initial

    def configure(self, store: T) -> None:
        """由 persistence.bootstrap 在启动时注入 Postgres 或内存实现。"""
        self._inner = store

    @property
    def inner(self) -> T:
        """测试或诊断时读取当前后端实现。"""
        return self._inner

    def __getattr__(self, name: str) -> Any:
        """未在代理上定义的属性/方法，一律转发到 _inner。"""
        return getattr(self._inner, name)
