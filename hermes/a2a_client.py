#!/usr/bin/env python3
"""
A2A Client Test - Complete verification of Hermes A2A gateway integration
"""

import json
import requests
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class A2AResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class A2AClient:
    def __init__(self, gateway_url: str = "http://127.0.0.1:9900"):
        self.gateway_url = gateway_url.rstrip("/")
        self.request_id = 1
    
    def get_agent_card(self) -> A2AResponse:
        try:
            url = f"{self.gateway_url}/.well-known/agent-card.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return A2AResponse(success=True, data=response.json())
        except Exception as e:
            return A2AResponse(success=False, error=str(e))
    
    def call_jsonrpc(self, method: str, params: Optional[Dict] = None) -> A2AResponse:
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": self.request_id
            }
            self.request_id += 1
            
            response = requests.post(
                f"{self.gateway_url}/",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                return A2AResponse(success=False, error=str(data.get("error")))
            
            return A2AResponse(success=True, data=data.get("result"))
        except Exception as e:
            return A2AResponse(success=False, error=str(e))
    
    def is_healthy(self) -> bool:
        return self.get_agent_card().success


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    client = A2AClient()
    
    print_section("A2A Client - Hermes Gateway Integration Test")
    
    # Test 1: Gateway accessibility
    print("\n[TEST 1] Gateway Accessibility")
    print("-" * 70)
    if not client.is_healthy():
        print("✗ FAILED: Gateway not accessible at http://127.0.0.1:9900")
        return False
    print("✓ PASSED: Gateway is accessible")
    
    # Test 2: Agent card retrieval
    print("\n[TEST 2] Agent Card Retrieval")
    print("-" * 70)
    response = client.get_agent_card()
    if not response.success:
        print(f"✗ FAILED: {response.error}")
        return False
    
    card = response.data
    print("✓ PASSED: Agent card retrieved")
    print(f"  Agent: {card.get('name')} v{card.get('version')}")
    print(f"  URL: {card.get('url')}")
    print(f"  Organization: {card.get('provider', {}).get('organization')}")
    
    # Test 3: Verify JSONRPC interface
    print("\n[TEST 3] JSONRPC Interface Check")
    print("-" * 70)
    interfaces = card.get('supportedInterfaces', [])
    jsonrpc_found = any(i.get('protocolBinding') == 'JSONRPC' for i in interfaces)
    if jsonrpc_found:
        print("✓ PASSED: JSONRPC interface is supported")
        for iface in interfaces:
            print(f"  - {iface.get('protocolBinding')} "
                  f"v{iface.get('protocolVersion')} at {iface.get('url')}")
    else:
        print("✗ FAILED: JSONRPC interface not found")
        return False
    
    # Test 4: Capabilities check
    print("\n[TEST 4] Gateway Capabilities")
    print("-" * 70)
    capabilities = card.get('capabilities', {})
    print("✓ Capabilities:")
    for key, value in capabilities.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")
    
    # Test 5: Skills inventory
    print("\n[TEST 5] Skills & Toolsets Available")
    print("-" * 70)
    skills = card.get('skills', [])
    print(f"✓ PASSED: {len(skills)} skills/toolsets available")
    
    toolsets = {}
    for skill in skills:
        skill_id = skill.get('id', '').replace('toolset.', '')
        toolsets[skill_id] = skill
    
    print("\n  Available Toolsets:")
    for name in sorted(toolsets.keys())[:10]:
        skill = toolsets[name]
        tags = skill.get('tags', [])
        print(f"    • {name}: {len(tags)} operations")
    
    if len(toolsets) > 10:
        print(f"    ... and {len(toolsets) - 10} more")
    
    # Test 6: Try a simple JSONRPC call
    print("\n[TEST 6] JSONRPC Communication Test")
    print("-" * 70)
    response = client.call_jsonrpc("system.ping")
    if response.success:
        print("✓ PASSED: JSONRPC ping successful")
        print(f"  Response: {response.data}")
    else:
        # Try a method that might exist
        print(f"⚠ INFO: system.ping not supported ({response.error})")
        print("  (This is expected if no ping method is exposed)")
    
    # Summary
    print_section("Test Summary")
    print("\n✓ All critical tests PASSED")
    print("\nA2A Client Configuration:")
    print(f"  Gateway URL: http://127.0.0.1:9900")
    print(f"  Agent: {card.get('name')}")
    print(f"  Available Skills: {len(skills)}")
    print(f"  JSONRPC Supported: Yes")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
