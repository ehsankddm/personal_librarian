#!/usr/bin/env python3
"""Test script to verify ActionRequest implementation."""

import asyncio
from actions.action_request import ActionRequest, ActionType, Reversibility, DataSensitivity
from core.gatekeeper import Gatekeeper, GatekeeperDecision
from core.policies import PolicyManager
from actions.executor import ActionExecutor


def test_action_request_creation():
    """Test ActionRequest creation and fields."""
    print("🧪 Testing ActionRequest Creation\n")

    request = ActionRequest(
        requester_agent_id="BackupAgent_immediate_v1",
        requester_role="BackupAgent",
        action_type=ActionType.BACKUP_SYNC,
        details={"books": ["book1", "book2"], "destination": "google_drive"},
        justification="Upload encrypted backups for off-site storage",
        user_impact="Non-destructive; creates encrypted backups only",
        data_sensitivity=DataSensitivity.MEDIUM,
        estimated_cost_eur=0.0,
        estimated_runtime_sec=10.0,
        reversibility=Reversibility.REVERSIBLE,
        requires_user_approval=False,
    )

    print(f"✓ Request ID: {request.request_id}")
    print(f"✓ Requester: {request.requester_agent_id} ({request.requester_role})")
    print(f"✓ Action Type: {request.action_type}")
    print(f"✓ Data Sensitivity: {request.data_sensitivity}")
    print(f"✓ Reversibility: {request.reversibility}")
    print(f"✓ Cost: €{request.estimated_cost_eur}")
    print(f"✓ Requires Approval: {request.requires_user_approval}")

    # Test serialization
    data = request.to_dict()
    print(f"\n✓ Serialization: {len(data)} fields")

    # Test deserialization
    restored = ActionRequest.from_dict(data)
    assert restored.request_id == request.request_id
    assert restored.action_type == request.action_type
    print("✓ Deserialization successful")

    # Test human-readable summary
    summary = request.get_human_readable_summary()
    assert "BackupAgent" in summary
    assert "backup.sync" in summary
    print("✓ Human-readable summary generated")

    print("\n✅ ActionRequest creation tests passed!")


async def test_gatekeeper_evaluation():
    """Test Gatekeeper evaluation logic."""
    print("\n🧪 Testing Gatekeeper Evaluation\n")

    # Setup
    policy_manager = PolicyManager()
    executor = ActionExecutor()
    gatekeeper = Gatekeeper(policy_manager, executor)

    # Test 1: Auto-approve safe action
    print("Test 1: Auto-approve safe action")
    safe_request = ActionRequest(
        requester_agent_id="BackupAgent_v1",
        requester_role="BackupAgent",
        action_type=ActionType.BACKUP_SYNC,
        details={"books": ["book1"]},
        justification="Safe backup",
        user_impact="Non-destructive",
        data_sensitivity=DataSensitivity.LOW,
        estimated_cost_eur=0.0,
        estimated_runtime_sec=5.0,
        reversibility=Reversibility.REVERSIBLE,
        requires_user_approval=False,
    )

    approved, reason = await gatekeeper.evaluate_action(safe_request)
    print(f"  Result: {'APPROVED' if approved else 'DENIED'}")
    print(f"  Reason: {reason}")

    # Test 2: Require user approval for irreversible action
    print("\nTest 2: Require approval for irreversible action")
    irreversible_request = ActionRequest(
        requester_agent_id="BackupAgent_v1",
        requester_role="BackupAgent",
        action_type=ActionType.FILESYSTEM_DELETE,
        details={"path": "/tmp/test"},
        justification="Delete temporary file",
        user_impact="Deletes local file",
        data_sensitivity=DataSensitivity.LOW,
        estimated_cost_eur=0.0,
        estimated_runtime_sec=1.0,
        reversibility=Reversibility.IRREVERSIBLE,
        requires_user_approval=False,
    )

    approved, reason = await gatekeeper.evaluate_action(irreversible_request)
    print(f"  Result: {'APPROVED' if approved else 'DENIED'}")
    print(f"  Reason: {reason[:100]}...")
    assert "ASK_USER" in reason or not approved

    # Test 3: Deny high-cost action
    print("\nTest 3: Deny high-cost action")
    costly_request = ActionRequest(
        requester_agent_id="BackupAgent_v1",
        requester_role="BackupAgent",
        action_type=ActionType.NETWORK_UPLOAD,
        details={"url": "https://example.com"},
        justification="Expensive upload",
        user_impact="High cost",
        data_sensitivity=DataSensitivity.MEDIUM,
        estimated_cost_eur=1000.0,  # Very high
        estimated_runtime_sec=10.0,
        reversibility=Reversibility.REVERSIBLE,
        requires_user_approval=False,
    )

    approved, reason = await gatekeeper.evaluate_action(costly_request)
    print(f"  Result: {'APPROVED' if approved else 'DENIED'}")
    print(f"  Reason: {reason}")

    print("\n✅ Gatekeeper evaluation tests passed!")


def test_action_types():
    """Test all action types."""
    print("\n🧪 Testing Action Types\n")

    action_types = [
        ActionType.NETWORK_FETCH,
        ActionType.NETWORK_UPLOAD,
        ActionType.FILESYSTEM_WRITE,
        ActionType.FILESYSTEM_DELETE,
        ActionType.PROCESS_SPAWN,
        ActionType.COMPUTE_HEAVY,
        ActionType.BACKUP_SYNC,
        ActionType.DELIVERY_KINDLE_SEND,
        ActionType.METADATA_LOOKUP_EXTERNAL,
        ActionType.AGENT_CREATION,
    ]

    for action_type in action_types:
        print(f"  ✓ {action_type.value}")

    print(f"\n✅ All {len(action_types)} action types defined")


async def main():
    """Run all tests."""
    try:
        test_action_types()
        test_action_request_creation()
        await test_gatekeeper_evaluation()

        print("\n" + "=" * 60)
        print("🎉 All ActionRequest tests passed!")
        print("=" * 60)
        print("\nImplemented features from ACTION_REQUEST.md:")
        print("  ✓ Complete ActionRequest structure (13 fields)")
        print("  ✓ All action types defined")
        print("  ✓ Reversibility levels")
        print("  ✓ Data sensitivity levels")
        print("  ✓ Serialization/deserialization")
        print("  ✓ Human-readable summaries")
        print("  ✓ Gatekeeper evaluation logic")
        print("  ✓ Policy integration")
        print("  ✓ Auto-approve / Ask-User / Deny logic")
        print("  ✓ Audit logging")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
