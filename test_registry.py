#!/usr/bin/env python3
"""Test script to verify Registry implementation."""

import asyncio
from pathlib import Path
from core.registry import Registry, SafetyProfile
from memory.society_memory import SocietyMemory


async def test_registry():
    """Test Registry functionality."""
    print("🧪 Testing Registry Implementation\n")
    
    # Clean up any existing test state
    test_path = Path("state/test_registry_state.json")
    if test_path.exists():
        test_path.unlink()
    
    # Initialize components
    print("📦 Initializing Registry...")
    registry = Registry(persistence_path=str(test_path))
    society_memory = SocietyMemory(base_path="memory")
    
    print("✓ Registry initialized")
    
    # Test 1: Register agent
    print("\n✓ Test 1: register_agent")
    registry.register_agent(
        agent_id="BackupAgent_immediate_v5",
        role="BackupAgent",
        capabilities_summary="I encrypt new books and immediately back them up to Drive.",
        traits={"strategy": "immediate_after_index", "llm_style": "short_bullets"},
        instinct_paths=["instincts/default_agent_instinct.md"],
        safety_profile=SafetyProfile(needs_network=True, touches_user_data=True),
        society_memory=society_memory
    )
    print(f"  Registered: BackupAgent_immediate_v5")
    
    # Test 2: Get agent
    print("\n✓ Test 2: get_agent")
    agent = registry.get_agent("BackupAgent_immediate_v5")
    assert agent is not None
    print(f"  Agent ID: {agent.agent_id}")
    print(f"  Role: {agent.role}")
    print(f"  Status: {agent.status}")
    
    # Test 3: Register second agent
    print("\n✓ Test 3: Register second agent")
    registry.register_agent(
        agent_id="BackupAgent_batch_v2",
        role="BackupAgent",
        capabilities_summary="I batch backups at night.",
        traits={"strategy": "batch_nightly"},
        safety_profile=SafetyProfile(needs_network=True),
        society_memory=society_memory
    )
    print(f"  Registered: BackupAgent_batch_v2")
    
    # Test 4: List candidates
    print("\n✓ Test 4: list_candidates")
    candidates = registry.list_candidates(role="BackupAgent")
    print(f"  Found {len(candidates)} BackupAgent candidates")
    assert len(candidates) == 2
    
    # Test 5: Filter by traits
    print("\n✓ Test 5: Filter by traits")
    immediate_candidates = registry.list_candidates(
        role="BackupAgent",
        required_traits={"strategy": "immediate_after_index"}
    )
    print(f"  Found {len(immediate_candidates)} immediate strategy candidates")
    assert len(immediate_candidates) == 1
    
    # Test 6: Policy filtering
    print("\n✓ Test 6: Policy filtering")
    no_network_candidates = registry.list_candidates(
        role="BackupAgent",
        policy_context={"network_allowed": False}
    )
    print(f"  Candidates without network requirement: {len(no_network_candidates)}")
    assert len(no_network_candidates) == 0
    
    # Test 7: Update performance
    print("\n✓ Test 7: update_performance")
    registry.update_performance(
        agent_id="BackupAgent_immediate_v5",
        reward_delta=1.5,
        success=True,
        latency_sec=4.2,
        escalated=False
    )
    agent = registry.get_agent("BackupAgent_immediate_v5")
    print(f"  Success count: {agent.performance.success_count}")
    print(f"  Avg reward: {agent.performance.avg_reward:.2f}")
    assert agent.performance.success_count == 1
    assert agent.performance.avg_reward > 0
    
    # Test 8: Get best replica
    print("\n✓ Test 8: get_best_replica")
    best = registry.get_best_replica("BackupAgent")
    print(f"  Best replica: {best}")
    assert best == "BackupAgent_immediate_v5"
    
    # Test 9: Quarantine
    print("\n✓ Test 9: quarantine")
    registry.quarantine(
        "BackupAgent_batch_v2",
        "Repeated policy violations",
        society_memory=society_memory
    )
    agent = registry.get_agent("BackupAgent_batch_v2")
    print(f"  Status after quarantine: {agent.status}")
    assert agent.status == "quarantined"
    
    # Test candidates after quarantine
    active_candidates = registry.list_candidates(role="BackupAgent")
    print(f"  Active candidates after quarantine: {len(active_candidates)}")
    assert len(active_candidates) == 1
    
    # Test 10: Retire
    print("\n✓ Test 10: retire")
    registry.retire(
        "BackupAgent_batch_v2",
        "Underperforming",
        society_memory=society_memory
    )
    agent = registry.get_agent("BackupAgent_batch_v2")
    print(f"  Status after retirement: {agent.status}")
    print(f"  Alive after retirement: {agent.alive}")
    assert agent.status == "retired"
    assert not agent.alive
    
    # Test 11: Persistence
    print("\n✓ Test 11: Persistence")
    registry2 = Registry(persistence_path=str(test_path))
    agent = registry2.get_agent("BackupAgent_immediate_v5")
    assert agent is not None
    print(f"  Loaded agent: {agent.agent_id}")
    
    # Test 12: Statistics
    print("\n✓ Test 12: get_agent_stats")
    stats = registry.get_agent_stats()
    print(f"  Total agents: {stats['total_agents']}")
    print(f"  Active: {stats['active']}")
    print(f"  Quarantined: {stats['quarantined']}")
    print(f"  Retired: {stats['retired']}")
    
    # Cleanup
    if test_path.exists():
        test_path.unlink()
    
    print("\n🎉 All Registry tests passed!")
    print("\nImplemented features:")
    print("  ✓ AgentInfo with SafetyProfile and PerformanceMetrics")
    print("  ✓ Persistence to JSON")
    print("  ✓ register_agent with validation")
    print("  ✓ update_performance method")
    print("  ✓ list_candidates with filtering")
    print("  ✓ quarantine method")
    print("  ✓ retire method")
    print("  ✓ get_agent method")
    print("  ✓ Society memory integration")
    print("  ✓ Policy compatibility checking")
    print("  ✓ Statistics and helper methods")


if __name__ == "__main__":
    asyncio.run(test_registry())

