"""BPMN REST API 层单测（convert / validate / snapshot）。"""

from __future__ import annotations

import pytest

from app.api.bpmn import (
    BpmnConvertRequest,
    BpmnSnapshotSaveRequest,
    BpmnValidateRequest,
    convert_bpmn,
    get_thread_bpmn,
    save_thread_bpmn,
    validate_bpmn,
)
from app.services.session_store import clear_thread_bpmn_snapshot, get_thread_bpmn_snapshot


@pytest.mark.asyncio
async def test_convert_steps_to_document():
    body = BpmnConvertRequest(
        direction="steps_to_document",
        steps=[
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
        ],
    )
    resp = await convert_bpmn(body)
    assert resp["code"] == 0
    doc = resp["data"]["flow_document"]
    assert isinstance(doc.get("nodes"), list)
    assert any(n.get("type") in ("AUTO", "MANUAL") for n in doc["nodes"])


@pytest.mark.asyncio
async def test_convert_document_to_steps_merge():
    from app.services.bpmn_orchestration import plan_steps_to_flow_document

    previous = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "skipped"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "awaiting_confirm"},
    ]
    doc = plan_steps_to_flow_document(previous)
    doc["nodes"] = [n for n in doc["nodes"] if n.get("id") != "2"]
    doc["edges"] = [
        {"sourceNodeID": "start_0", "targetNodeID": "1"},
        {"sourceNodeID": "1", "targetNodeID": "end_0"},
    ]
    body = BpmnConvertRequest(
        direction="document_to_steps",
        flow_document=doc,
        previous_steps=previous,
    )
    resp = await convert_bpmn(body)
    assert resp["code"] == 0
    steps = resp["data"]["steps"]
    assert len(steps) == 1
    assert steps[0]["tool"] == "query_alarms"
    assert steps[0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_validate_bpmn_rejects_empty_tool():
    from app.services.bpmn_orchestration import plan_steps_to_flow_document

    doc = plan_steps_to_flow_document(
        [{"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"}]
    )
    for node in doc["nodes"]:
        if node.get("id") == "1":
            node["data"]["tool"] = ""
    resp = await validate_bpmn(BpmnValidateRequest(flow_document=doc))
    assert resp["code"] == 0
    assert resp["data"]["valid"] is False


@pytest.mark.asyncio
async def test_thread_bpmn_snapshot_roundtrip():
    from app.services.bpmn_orchestration import plan_steps_to_flow_document

    tid = "thread-bpmn-api-test"
    clear_thread_bpmn_snapshot(tid)
    steps = [{"id": "1", "label": "查询", "tool": "query_alarms", "status": "done"}]
    doc = plan_steps_to_flow_document(steps)
    save_resp = await save_thread_bpmn(
        tid,
        BpmnSnapshotSaveRequest(flow_document=doc, steps=steps),
    )
    assert save_resp["code"] == 0
    assert get_thread_bpmn_snapshot(tid) is not None

    get_resp = await get_thread_bpmn(tid)
    assert get_resp["code"] == 0
    assert get_resp["data"]["snapshot"]["flow_document"]["nodes"]

    clear_thread_bpmn_snapshot(tid)
