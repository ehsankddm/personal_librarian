import pytest

from actions.action_request import ActionRequest, ActionType, Reversibility, DataSensitivity
from actions.executor import ActionExecutor
from core.gatekeeper import Gatekeeper
from core.policies import PolicyManager


@pytest.mark.asyncio
async def test_gatekeeper_denies_disallowed_action(tmp_path):
    policies = PolicyManager(policies_path=str(tmp_path / "policies.json"))
    # Default network.allow_external_requests is False
    gatekeeper = Gatekeeper(policies, ActionExecutor())

    req = ActionRequest(
        requester_agent_id="TestAgent",
        requester_role="Tester",
        action_type=ActionType.NETWORK_FETCH,
        justification="Fetch metadata",
    )

    approved, reason = await gatekeeper.evaluate_action(req)
    assert approved is False
    assert "Policy violation" in reason


@pytest.mark.asyncio
async def test_gatekeeper_asks_user_for_sensitive_action(tmp_path):
    policies = PolicyManager(policies_path=str(tmp_path / "policies.json"))
    # Allow network to pass policy check
    policies.set("network.allow_external_requests", True, check_lock=False)
    gatekeeper = Gatekeeper(policies, ActionExecutor())

    req = ActionRequest(
        requester_agent_id="TestAgent",
        requester_role="Tester",
        action_type=ActionType.NETWORK_FETCH,
        justification="Fetch sensitive content",
        data_sensitivity=DataSensitivity.HIGH,
    )

    approved, reason = await gatekeeper.evaluate_action(req)
    # Approved but requires user (encoded as ASK_USER prefix)
    assert approved is True
    assert reason.startswith("ASK_USER:")


@pytest.mark.asyncio
async def test_gatekeeper_execute_action(tmp_path):
    policies = PolicyManager(policies_path=str(tmp_path / "policies.json"))
    policies.set("filesystem.allow_delete", False, check_lock=False)
    gatekeeper = Gatekeeper(policies, ActionExecutor())

    req = ActionRequest(
        requester_agent_id="TestAgent",
        requester_role="Tester",
        action_type=ActionType.FILESYSTEM_WRITE,
        justification="Write safe file",
    )

    approved, _ = await gatekeeper.evaluate_action(req)
    assert approved is True

    success, result = await gatekeeper.execute_action(req)
    assert success is True
    assert isinstance(result, dict) and result.get("status") == "executed"
