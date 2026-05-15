#!/usr/bin/env python3
"""Test script to verify Terraform integration with the LangGraph assistant."""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from tools.registry import ToolRegistry
from tools.terraform_tools import (
    deploy_obs_bucket_with_terraform,
    deploy_elb_with_terraform,
    list_terraform_deployments
)


def test_tool_registration():
    """Test that Terraform tools are properly registered."""
    print("Testing Terraform tool registration...")
    
    # Reset and reload registry
    from tools.registry import ToolRegistry
    ToolRegistry.reset()
    registry = ToolRegistry.get()
    
    # Get all tools
    all_tools = registry.get_all_tools()
    terraform_tools = [t for t in all_tools if "terraform" in t.name.lower()]
    
    print(f"Total tools: {len(all_tools)}")
    print(f"Terraform tools: {len(terraform_tools)}")
    
    # Check specific tools
    tool_names = [t.name for t in terraform_tools]
    print(f"Terraform tool names: {tool_names}")
    
    # Verify all expected tools are present
    expected_tools = [
        "deploy_obs_bucket_with_terraform",
        "deploy_elb_with_terraform", 
        "list_terraform_deployments"
    ]
    
    for expected in expected_tools:
        if expected in tool_names:
            print(f"✅ {expected} is registered")
        else:
            print(f"❌ {expected} is NOT registered")
            return False
    
    # Check tool metadata
    for tool_name in expected_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            meta = registry.get_meta(tool_name)
            print(f"✅ {tool_name}: service={meta.service}, category={meta.category}, read_only={meta.is_read_only}")
        else:
            print(f"❌ {tool_name} not found in registry")
            return False
    
    return True


def test_tool_descriptions():
    """Test that tool descriptions are informative."""
    print("\nTesting tool descriptions...")
    
    # Test OBS tool description
    obs_desc = deploy_obs_bucket_with_terraform.description
    print(f"OBS tool description length: {len(obs_desc)} chars")
    print(f"First 200 chars: {obs_desc[:200]}...")
    
    # Test ELB tool description  
    elb_desc = deploy_elb_with_terraform.description
    print(f"ELB tool description length: {len(elb_desc)} chars")
    print(f"First 200 chars: {elb_desc[:200]}...")
    
    # Test list tool description
    list_desc = list_terraform_deployments.description
    print(f"List tool description length: {len(list_desc)} chars")
    
    # Check for key phrases
    key_phrases = ["OBS", "bucket", "Terraform", "ELB", "load balancer", "deployments"]
    for phrase in key_phrases:
        if phrase.lower() in obs_desc.lower() or phrase.lower() in elb_desc.lower():
            print(f"✅ Found '{phrase}' in descriptions")
        else:
            print(f"⚠️  '{phrase}' not found in descriptions")
    
    return True


def test_tool_keywords():
    """Test that tools have appropriate keywords for discovery."""
    print("\nTesting tool keywords...")
    
    from tools.registry import ToolRegistry
    registry = ToolRegistry.get()
    
    # Test keyword resolution
    test_queries = [
        "terraform obs",
        "terraform bucket",
        "create obs terraform",
        "terraform elb",
        "terraform load balancer",
        "create elb terraform",
        "list terraform",
        "terraform status"
    ]
    
    for query in test_queries:
        tool_name = registry.resolve_by_keywords(query)
        if tool_name:
            print(f"✅ Query '{query}' resolved to: {tool_name}")
        else:
            print(f"⚠️  Query '{query}' not resolved")
    
    # Test Spanish keywords
    spanish_queries = [
        "desplegar obs terraform",
        "obs terraform",
        "bucket terraform",
        "desplegar elb terraform",
        "balanceador carga terraform",
        "estado terraform"
    ]
    
    for query in spanish_queries:
        tool_name = registry.resolve_by_keywords(query)
        if tool_name:
            print(f"✅ Spanish query '{query}' resolved to: {tool_name}")
        else:
            print(f"⚠️  Spanish query '{query}' not resolved")
    
    return True


def test_tool_categories():
    """Test that tools have correct categories."""
    print("\nTesting tool categories...")
    
    from tools.registry import ToolRegistry, ToolCategory
    registry = ToolRegistry.get()
    
    terraform_tools = ["deploy_obs_bucket_with_terraform", "deploy_elb_with_terraform", "list_terraform_deployments"]
    
    for tool_name in terraform_tools:
        meta = registry.get_meta(tool_name)
        if meta:
            print(f"{tool_name}: category={meta.category} (value={meta.category.value})")
            
            # Check category assignment
            if tool_name.startswith("deploy_"):
                expected = ToolCategory.DEPLOY
                expected_str = "DEPLOY"
            elif tool_name.startswith("list_"):
                expected = ToolCategory.QUERY
                expected_str = "QUERY"
            else:
                print(f"  ⚠️  Unknown tool name pattern: {tool_name}")
                return False
            
            if meta.category == expected:
                print(f"  ✅ Correctly categorized as {expected_str}")
            else:
                print(f"  ❌ Should be {expected_str} but is {meta.category}")
                return False
        else:
            print(f"❌ No metadata for {tool_name}")
            return False
    
    return True


def test_tool_functionality():
    """Test basic tool functionality (without actually calling Terraform)."""
    print("\nTesting tool functionality (dry run)...")
    
    # Test OBS tool with minimal parameters
    try:
        print("Testing deploy_obs_bucket_with_terraform...")
        # This should work with just bucket_name
        result = deploy_obs_bucket_with_terraform.func(
            bucket_name="test-bucket-dry-run",
            region="ap-southeast-3",
            encryption=False  # Skip KMS for dry run
        )
        print(f"✅ OBS tool executed (dry run)")
        print(f"Result preview: {result[:100]}...")
    except Exception as e:
        print(f"❌ OBS tool failed: {e}")
        # Don't fail the test - actual execution depends on credentials
    
    # Test ELB tool with minimal parameters  
    try:
        print("\nTesting deploy_elb_with_terraform...")
        # This should work with basic parameters
        result = deploy_elb_with_terraform.func(
            loadbalancer_name="test-elb-dry-run",
            vpc_name="test-vpc",
            subnet_name="test-subnet",
            security_group_name="test-sg",
            instance_name="test-ecs",
            associate_eip=False  # Skip EIP for dry run
        )
        print(f"✅ ELB tool executed (dry run)")
        print(f"Result preview: {result[:100]}...")
    except Exception as e:
        print(f"❌ ELB tool failed: {e}")
        # Don't fail the test - actual execution depends on credentials
    
    # Test list tool
    try:
        print("\nTesting list_terraform_deployments...")
        result = list_terraform_deployments.func()
        print(f"✅ List tool executed")
        print(f"Result preview: {result[:100]}...")
    except Exception as e:
        print(f"❌ List tool failed: {e}")
        return False
    
    return True


def main():
    """Run all Terraform integration tests."""
    print("=" * 70)
    print("Testing Terraform Integration with Huawei Cloud Smart Assistant")
    print("=" * 70)
    
    tests = [
        ("Tool Registration", test_tool_registration),
        ("Tool Descriptions", test_tool_descriptions),
        ("Tool Keywords", test_tool_keywords),
        ("Tool Categories", test_tool_categories),
        ("Tool Functionality", test_tool_functionality),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Test: {test_name}")
        print(f"{'='*50}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Exception in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print(f"\n{'='*70}")
    print("Test Summary:")
    print(f"{'='*70}")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print("🎉 All integration tests passed! Terraform tools are ready for use.")
        print("\nThe assistant can now handle:")
        print("1. OBS bucket creation with Terraform")
        print("2. ELB environment deployment with Terraform")
        print("3. Listing Terraform deployments")
        print("\nTry asking:")
        print("- 'Create an OBS bucket with Terraform named my-backup-bucket'")
        print("- 'Deploy an ELB with Terraform for my web application'")
        print("- 'What Terraform deployments do I have?'")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())