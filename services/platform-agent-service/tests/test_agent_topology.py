"""D4：父图拓扑与真实节点集合一致。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langgraph.checkpoint.memory import InMemorySaver

from app.graph.parent_graph import get_agent_topology, reset_parent_graph_cache


def test_get_agent_topology_contains_core_nodes():
    reset_parent_graph_cache()
    fake_agent = MagicMock(name="fake_agent")
    with (
        patch("app.graph.agent_factory.get_agent", return_value=fake_agent),
        patch("app.graph.agent_factory.get_chat_agent", return_value=fake_agent),
        patch(
            "app.graph.agent_factory._get_checkpointer",
            return_value=InMemorySaver(),
        ),
    ):
        topo = get_agent_topology(model_id="test-model")
    ids = {n["id"] for n in topo["nodes"]}
    required = {
        "classify",
        "plan_confirm",
        "device_gate",
        "plan_execute",
        "bpmn_execute",
        "react",
        "chat_direct",
    }
    assert required <= ids
    assert topo["engine"] == "parent_state_graph"
    assert isinstance(topo.get("edges"), list)
    reset_parent_graph_cache()
