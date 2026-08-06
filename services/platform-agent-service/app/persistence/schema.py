"""
Agent 业务表 DDL

LangGraph checkpoint 表由 AsyncPostgresSaver.setup() 创建；
本模块仅建会话、消息索引、Trace、审计、BPMN 快照等业务表。
"""

AGENT_APP_DDL = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '新会话',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_updated
    ON agent_sessions (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS agent_thread_user_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_thread_user_messages_thread
    ON agent_thread_user_messages (thread_id, id DESC);

CREATE TABLE IF NOT EXISTS agent_thread_traces (
    thread_id TEXT NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, run_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_thread_traces_thread_started
    ON agent_thread_traces (thread_id, started_at DESC);

CREATE TABLE IF NOT EXISTS agent_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    run_id TEXT,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tool_name TEXT,
    payload_summary JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_thread_created
    ON agent_audit_logs (thread_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_user_created
    ON agent_audit_logs (user_id, created_at DESC);

-- BPMN 级编排快照（plan_confirm 编排草稿 / 批准后持久化）
CREATE TABLE IF NOT EXISTS agent_thread_bpmn (
    thread_id TEXT PRIMARY KEY REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    snapshot JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- chat 绑定的工具子集指纹（resume 跨进程复用同一父图）
CREATE TABLE IF NOT EXISTS agent_thread_tool_subset (
    thread_id TEXT PRIMARY KEY REFERENCES agent_sessions(thread_id) ON DELETE CASCADE,
    tool_names JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 声纹档案（元数据；向量在 Qdrant collection agent_voiceprints）
CREATE TABLE IF NOT EXISTS agent_voiceprint_profiles (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    model_id TEXT NOT NULL DEFAULT '',
    sample_count INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_voiceprint_profiles_updated
    ON agent_voiceprint_profiles (updated_at DESC);

CREATE TABLE IF NOT EXISTS agent_voiceprint_samples (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES agent_voiceprint_profiles(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    duration_ms INT NOT NULL DEFAULT 0,
    device_hint TEXT NOT NULL DEFAULT '',
    env_hint TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_voiceprint_samples_profile
    ON agent_voiceprint_samples (profile_id);
"""

# 旧图外 HITL 暂存表：零兼容后删除（IF EXISTS，可重复执行）
_DROP_LEGACY_PENDING_DDL = """
DROP TABLE IF EXISTS agent_thread_pending;
"""

# 旧单向量声纹表：破坏性删除（见 docs/architecture/11-voiceprint.md）
_DROP_LEGACY_VOICEPRINT_DDL = """
DROP TABLE IF EXISTS agent_voiceprints;
"""


def setup_app_tables(conn) -> None:
    """
    创建或确保 Agent 业务表存在，并清理已废弃的 pending HITL / 旧声纹表。

    参数：
        conn: psycopg 连接，需支持 conn.execute(sql)
    """
    conn.execute(_DROP_LEGACY_VOICEPRINT_DDL)
    conn.execute(AGENT_APP_DDL)
    conn.execute(_DROP_LEGACY_PENDING_DDL)
