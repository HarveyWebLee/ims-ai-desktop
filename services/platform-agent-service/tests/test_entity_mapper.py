"""实体行映射单测。"""

from app.sync.entity_mapper import map_row_to_entity


def test_map_device():
    mapped = map_row_to_entity(
        "p_device",
        {"device_code": "D1", "device_name": "东门", "area_name": "周界"},
        0,
    )
    assert mapped["entity_type"] == "device"
    assert mapped["source"] == "dm:device:D1"
    assert "东门" in mapped["text"]


def test_map_variable():
    mapped = map_row_to_entity(
        "p_device_variable",
        {
            "device_code": "D1",
            "var_name": "status_door",
            "show_name": "门状态",
        },
        0,
    )
    assert mapped["entity_type"] == "variable"
    assert mapped["source"] == "dm:variable:D1:status_door"


def test_map_generic():
    mapped = map_row_to_entity("other_table", {"id": 9, "title": "x"}, 0)
    assert mapped["entity_type"] == "table_row"
    assert mapped["source"] == "dm:table:other_table:9"
