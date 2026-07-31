"""实体同步服务错误分支测试。"""

from app.sync import entity_sync_service as svc


def test_dm_connect_error_returns_skipped(monkeypatch):
    monkeypatch.setattr(svc.settings, "entity_sync_tables", "p_device")
    monkeypatch.setattr(svc.settings, "dm_read_only", True)
    monkeypatch.setattr(svc.settings, "dm_host", "127.0.0.1")
    monkeypatch.setattr(svc.settings, "dm_user", "u")
    monkeypatch.setattr(svc.settings, "dm_password", "p")
    monkeypatch.setattr(svc.settings, "qdrant_url", "http://127.0.0.1:16333")

    def _boom():
        raise svc.dm.DamengReadOnlyError("未安装 dmPython")

    monkeypatch.setattr(svc.dm, "list_user_tables", _boom)

    result = svc.run_entity_sync()
    assert result["ok"] is False
    assert result["skipped"] is True
    assert result["reason"] == "dm_connect_error"
    assert "dmPython" in result["message"]
