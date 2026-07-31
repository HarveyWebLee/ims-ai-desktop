"""ENTITY_SYNC_TABLES 解析单测。"""

from app.sync.table_config import parse_entity_sync_tables


def test_empty_skips():
    plan = parse_entity_sync_tables("")
    assert plan.skip is True
    assert plan.all_tables is False
    assert plan.explicit_tables == ()


def test_star_all_tables():
    plan = parse_entity_sync_tables("*")
    assert plan.skip is False
    assert plan.all_tables is True


def test_comma_list_dedupe_lower():
    plan = parse_entity_sync_tables("p_device, P_DEVICE_VARIABLE , p_device")
    assert plan.skip is False
    assert plan.all_tables is False
    assert plan.explicit_tables == ("p_device", "p_device_variable")


def test_whitespace_only_skips():
    plan = parse_entity_sync_tables("  ,  , ")
    assert plan.skip is True
