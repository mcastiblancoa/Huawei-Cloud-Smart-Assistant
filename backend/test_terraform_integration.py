#!/usr/bin/env python3
"""Test script for Terraform integration with Huawei Cloud Smart Assistant."""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from tools.terraform_manager import TerraformManager
from config.settings import get_settings


def test_terraform_manager():
    """Test the TerraformManager class."""
    print("Testing TerraformManager...")
    
    # Initialize settings
    settings = get_settings()
    print(f"Using region: {settings.huawei_region}")
    print(f"Access key available: {'Yes' if settings.huawei_ak else 'No'}")
    print(f"Secret key available: {'Yes' if settings.huawei_sk else 'No'}")
    
    # Create Terraform manager
    tf_manager = TerraformManager()
    print(f"Terraform working directory: {tf_manager.working_dir}")
    
    # Test credentials retrieval
    credentials = tf_manager._get_credentials()
    print(f"Credentials keys: {list(credentials.keys())}")
    
    print("\n✅ TerraformManager initialized successfully!")
    return True


def test_obs_module_structure():
    """Test that OBS module files exist."""
    print("\nTesting OBS module structure...")
    
    # Go up one level to project root
    project_root = backend_dir.parent
    obs_module_dir = project_root / "terraform" / "modules" / "obs"
    required_files = ["main.tf", "variables.tf", "outputs.tf"]
    
    for file in required_files:
        file_path = obs_module_dir / file
        if file_path.exists():
            print(f"✅ {file} exists at {file_path}")
        else:
            print(f"❌ {file} missing at {file_path}")
            return False
    
    print("✅ OBS module structure is complete!")
    return True


def test_elb_module_structure():
    """Test that ELB module files exist."""
    print("\nTesting ELB module structure...")
    
    # Go up one level to project root
    project_root = backend_dir.parent
    elb_module_dir = project_root / "terraform" / "modules" / "elb"
    required_files = ["main.tf", "variables.tf"]
    
    for file in required_files:
        file_path = elb_module_dir / file
        if file_path.exists():
            print(f"✅ {file} exists at {file_path}")
        else:
            print(f"❌ {file} missing at {file_path}")
            return False
    
    print("✅ ELB module structure is complete!")
    return True


def test_tools_import():
    """Test that Terraform tools can be imported."""
    print("\nTesting Terraform tools import...")
    
    try:
        from tools.terraform_tools import (
            deploy_obs_bucket_with_terraform,
            deploy_elb_with_terraform,
            list_terraform_deployments,
            TERRAFORM_TOOLS
        )
        
        print(f"✅ Terraform tools imported successfully")
        print(f"✅ Number of Terraform tools: {len(TERRAFORM_TOOLS)}")
        
        # Check tool metadata
        for tool_meta in TERRAFORM_TOOLS:
            print(f"  - {tool_meta.tool.name}: {tool_meta.service} - {tool_meta.category}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Terraform tools: {e}")
        return False


def test_registry_integration():
    """Test that Terraform tools are registered in the ToolRegistry."""
    print("\nTesting ToolRegistry integration...")
    
    try:
        from tools.registry import ToolRegistry
        
        # Reset and reload registry
        ToolRegistry.reset()
        registry = ToolRegistry.get()
        
        # Check if Terraform tools are registered
        all_tools = registry.get_all_tools()
        terraform_tools = [t for t in all_tools if "terraform" in t.name.lower()]
        
        print(f"✅ Total tools in registry: {len(all_tools)}")
        print(f"✅ Terraform tools found: {len(terraform_tools)}")
        
        for tool in terraform_tools:
            print(f"  - {tool.name}")
        
        if len(terraform_tools) >= 2:
            print("✅ Terraform tools successfully registered!")
            return True
        else:
            print("❌ Not enough Terraform tools registered")
            return False
            
    except Exception as e:
        print(f"❌ Error testing registry: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Terraform Integration for Huawei Cloud Smart Assistant")
    print("=" * 60)
    
    tests = [
        ("TerraformManager", test_terraform_manager),
        ("OBS Module Structure", test_obs_module_structure),
        ("ELB Module Structure", test_elb_module_structure),
        ("Tools Import", test_tools_import),
        ("Registry Integration", test_registry_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"Test: {test_name}")
        print(f"{'='*40}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Exception in {test_name}: {e}")
            results.append((test_name, False))
    
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"{'='*60}")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 All tests passed! Terraform integration is ready.")
        print("\nNext steps:")
        print("1. Run the application: python run.py")
        print("2. Ask the assistant: 'Create an OBS bucket with Terraform'")
        print("3. Ask the assistant: 'Deploy an ELB with Terraform'")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())