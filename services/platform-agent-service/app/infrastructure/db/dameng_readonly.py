"""
达梦只读连接封装。

约束
----
- 仅允许 SELECT；SQL 预检拒绝写关键字
- 不提供 execute / commit 写接口
- 驱动优先 dmPython，其次 JayDeBeApi + DM_JDBC_JAR
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# 防御性：拒绝明显写语句（不替代账号只读权限）
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|"
    r"GRANT|REVOKE|CALL|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)


class DamengReadOnlyError(RuntimeError):
    """达梦只读访问失败。"""


def assert_dm_read_only_config() -> None:
    """配置层强制只读；禁止以可写意图启动同步。"""
    if not settings.dm_read_only:
        raise DamengReadOnlyError("DM_READ_ONLY 必须为 true：智能化侧禁止对平台达梦写操作")


def is_dm_configured() -> bool:
    """是否已配置达梦主机与账号（密码可为空字符串时仍视为未配齐则要求 password 非空更稳妥）。"""
    return bool(
        (settings.dm_host or "").strip()
        and (settings.dm_user or "").strip()
        and (settings.dm_password or "").strip()
    )


def _assert_select_only(sql: str) -> str:
    cleaned = (sql or "").strip()
    if not cleaned:
        raise DamengReadOnlyError("SQL 不能为空")
    # 去掉前导注释后必须以 SELECT 开头（允许 WITH ... SELECT）
    body = re.sub(r"^\s*--[^\n]*\n", "", cleaned, flags=re.MULTILINE).strip()
    upper = body.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise DamengReadOnlyError("只允许 SELECT / WITH…SELECT 查询")
    if _FORBIDDEN_SQL.search(body):
        raise DamengReadOnlyError("检测到禁止的写操作关键字，已拒绝执行")
    return cleaned


def _connect_dm_python() -> Any:
    try:
        import dmPython  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DamengReadOnlyError("未安装 dmPython") from exc

    return dmPython.connect(
        user=settings.dm_user,
        password=settings.dm_password,
        server=settings.dm_host.strip(),
        port=int(settings.dm_port),
    )


def _connect_jdbc() -> Any:
    jar = (settings.dm_jdbc_jar or "").strip()
    if not jar:
        raise DamengReadOnlyError("未安装 dmPython，且未配置 DM_JDBC_JAR（达梦 JDBC 驱动路径）")
    try:
        import jaydebeapi  # type: ignore[import-not-found]
    except ImportError as exc:
        raise DamengReadOnlyError(
            "未安装 JayDeBeApi；请 uv sync --extra entity-sync，或安装 dmPython"
        ) from exc

    url = f"jdbc:dm://{settings.dm_host.strip()}:{int(settings.dm_port)}"
    return jaydebeapi.connect(
        "dm.jdbc.driver.DmDriver",
        url,
        [settings.dm_user, settings.dm_password],
        jar,
    )


@contextmanager
def open_readonly_connection() -> Iterator[Any]:
    """打开只读连接；用毕关闭。"""
    assert_dm_read_only_config()
    if not is_dm_configured():
        raise DamengReadOnlyError("未配置 DM_HOST / DM_USER / DM_PASSWORD")

    conn: Any | None = None
    last_err: Exception | None = None
    for factory in (_connect_dm_python, _connect_jdbc):
        try:
            conn = factory()
            break
        except DamengReadOnlyError as exc:
            last_err = exc
            continue
        except Exception as exc:  # noqa: BLE001
            last_err = DamengReadOnlyError(f"达梦连接失败: {exc}")
            continue

    if conn is None:
        raise DamengReadOnlyError(str(last_err) if last_err else "无法连接达梦")

    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            logger.debug("关闭达梦连接时忽略异常", exc_info=True)


def _rows_from_cursor(cursor: Any) -> list[dict[str, Any]]:
    """将游标结果转为 list[dict]，列名统一小写。"""
    description = getattr(cursor, "description", None) or ()
    columns = [str(col[0]).lower() for col in description]
    rows: list[dict[str, Any]] = []
    for raw in cursor.fetchall() or []:
        # JDBC 可能返回 java 对象；统一 str/基础类型
        values: list[Any] = []
        for item in raw:
            if item is None or isinstance(item, (str, int, float, bool)):
                values.append(item)
            else:
                values.append(str(item))
        rows.append(dict(zip(columns, values, strict=False)))
    return rows


def fetch_all(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """执行只读查询并返回全部行（dict，键为小写列名）。"""
    safe_sql = _assert_select_only(sql)
    with open_readonly_connection() as conn:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(safe_sql, list(params))
            else:
                cursor.execute(safe_sql)
            return _rows_from_cursor(cursor)
        finally:
            try:
                cursor.close()
            except Exception:  # noqa: BLE001
                pass


def list_user_tables() -> list[str]:
    """列出当前用户可见基表名（小写）。"""
    # 达梦常见字典：USER_TABLES；失败时回退 ALL_TABLES
    schema = (settings.dm_schema or settings.dm_user or "").strip()
    try:
        rows = fetch_all("SELECT TABLE_NAME FROM USER_TABLES")
    except DamengReadOnlyError:
        raise
    except Exception:
        if schema:
            rows = fetch_all(
                "SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = ?",
                [schema.upper()],
            )
        else:
            rows = fetch_all("SELECT TABLE_NAME FROM USER_TABLES")

    names: list[str] = []
    for row in rows:
        name = str(row.get("table_name") or "").strip()
        if name:
            names.append(name.lower())
    return sorted(set(names))


def table_exists(table_name: str, available: list[str] | None = None) -> bool:
    """大小写不敏感判断表是否存在。"""
    needle = (table_name or "").strip().lower()
    if not needle:
        return False
    tables = available if available is not None else list_user_tables()
    return needle in {t.lower() for t in tables}


def resolve_table_name(table_name: str, available: list[str]) -> str | None:
    """在 available 中解析实际表名（返回 available 中的形式）。"""
    needle = (table_name or "").strip().lower()
    for name in available:
        if name.lower() == needle:
            return name
    return None


def fetch_table_rows(table_name: str, *, limit: int, offset: int = 0) -> list[dict[str, Any]]:
    """
    只读拉取表数据。

    使用双引号包裹标识符以保留大小写；limit 由调用方保证为正整数。
    """
    raw = (table_name or "").strip()
    if not raw or not re.fullmatch(r"[A-Za-z0-9_]+", raw):
        raise DamengReadOnlyError(f"非法表名: {table_name!r}")
    lim = max(1, int(limit))
    start = max(0, int(offset))
    end = start + lim
    # 达梦未加引号时标识符通常折成大写；按大写查询更稳
    quoted = raw.upper()
    sql = (
        f"SELECT * FROM ("
        f'SELECT t.*, ROWNUM AS __rn FROM (SELECT * FROM "{quoted}") t '
        f"WHERE ROWNUM <= {end}"
        f") WHERE __rn > {start}"
    )
    try:
        return fetch_all(sql)
    except Exception:
        # 回退：不加引号
        sql2 = (
            f"SELECT * FROM ("
            f"SELECT t.*, ROWNUM AS __rn FROM (SELECT * FROM {quoted}) t "
            f"WHERE ROWNUM <= {end}"
            f") WHERE __rn > {start}"
        )
        return fetch_all(sql2)
