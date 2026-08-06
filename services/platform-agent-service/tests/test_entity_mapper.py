"""实体行映射单测。"""

from app.sync.entity_mapper import map_row_to_entity


def test_map_device():
    mapped = map_row_to_entity(
        "p_device",
        {
            "id": 7931,
            "device_code": "AA10_1",
            "device_name": "AA10-1备用",
            "sub_system_id": 3,
            "sub_system_name": "电力监控子系统",
            "device_group_id": 47,
            "device_group_name": "PLC设备",
            "comm_device_id": 7924,
            "comm_device_code": "DLJK_1",
            "comm_device_name": "电力监控网关1",
            "collect_server_id": 8,
            "collect_server_name": "自测环境_数采服务192.168.15.91",
            "device_category_id": 12,
            "device_category_name": "控制器",
            "ip_address": "192.168.15.91",
            "user_name": "admin",
            "password": "should-never-store",
            "location": None,
            "lng_lat": None,
            "area_name": "周界",
            "online_status": "1",
        },
        0,
    )
    assert mapped["entity_type"] == "device"
    assert mapped["source"] == "dm:device:AA10_1"
    assert mapped["entity_key"] == "AA10_1"
    assert "AA10-1备用" in mapped["text"]
    assert "电力监控子系统" in mapped["text"]
    assert "周界" not in mapped["text"]
    assert "在线" not in mapped["text"]
    assert "admin" not in mapped["text"]

    payload = mapped["payload"]
    assert payload["id"] == 7931
    assert payload["deviceCode"] == "AA10_1"
    assert payload["deviceName"] == "AA10-1备用"
    assert payload["subSystemName"] == "电力监控子系统"
    assert payload["deviceGroupName"] == "PLC设备"
    assert payload["commDeviceCode"] == "DLJK_1"
    assert payload["collectServerId"] == 8
    assert payload["deviceCategoryName"] == "控制器"
    assert payload["ipAddress"] == "192.168.15.91"
    assert payload["userName"] == "admin"
    assert "password" not in payload
    assert "location" not in payload
    assert "lngLat" not in payload
    assert "area_name" not in payload
    assert "online_status" not in payload
    assert "table" not in payload


def test_map_device_ignores_password_column_variants():
    mapped = map_row_to_entity(
        "p_device",
        {"device_code": "D1", "device_name": "东门", "password": "secret", "passwd": "x"},
        0,
    )
    assert "password" not in mapped["payload"]
    assert "secret" not in mapped["text"]


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
