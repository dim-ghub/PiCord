#!/usr/bin/env python3
"""
Test script for Discord connectivity improvements
"""
import socket
import time
import subprocess
from typing import Optional

def check_network_connectivity(host: str = "discord.com", port: int = 443, timeout: int = 5) -> bool:
    """Check if network connectivity to Discord is available"""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except (socket.timeout, socket.error, OSError):
        return False

def resolve_gateway_fallback(hostname: str) -> Optional[str]:
    """Resolve gateway hostname with multiple DNS fallback attempts"""
    for attempt in range(3):
        try:
            # Try system DNS first
            result = socket.gethostbyname(hostname)
            print(f"Resolved {hostname} to {result} (attempt {attempt + 1})")
            return result
        except socket.gaierror:
            if attempt == 0:
                # Try Google DNS on first failure (if dnspython is available)
                try:
                    import dns.resolver
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = ['8.8.8.8', '8.8.4.4']
                    result = resolver.resolve(hostname, 'A')[0].address
                    print(f"Resolved {hostname} to {result} via Google DNS")
                    return result
                except ImportError:
                    print("dnspython not available, using alternative DNS resolution")
                except Exception as e:
                    print(f"Google DNS fallback failed: {e}")
            
            if attempt < 2:
                print(f"DNS resolution attempt {attempt + 1} failed for {hostname}, retrying...")
                time.sleep(1)
    
    print(f"Failed to resolve {hostname} after 3 attempts")
    return None

def test_alternative_dns(hostname: str) -> Optional[str]:
    """Try alternative DNS resolution using nslookup"""
    try:
        result = subprocess.run(['nslookup', hostname], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Parse nslookup output for IP address
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Address:' in line and not line.startswith('Server:'):
                    ip = line.split('Address:')[-1].strip()
                    if ip and '.' in ip:
                        print(f"Resolved {hostname} to {ip} via nslookup")
                        return ip
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
        print(f"Alternative DNS resolution failed: {e}")
    return None

if __name__ == "__main__":
    print("Testing Discord connectivity improvements...")
    
    # Test basic connectivity
    print("\n1. Testing basic connectivity to discord.com...")
    if check_network_connectivity():
        print("✅ Basic connectivity OK")
    else:
        print("❌ Basic connectivity FAILED")
    
    # Test DNS resolution
    print("\n2. Testing DNS resolution for gateway endpoints...")
    gateways = [
        "gateway-us-east1-c.discord.gg",
        "gateway-us-east1-b.discord.gg", 
        "gateway-us-central1-b.discord.gg",
        "gateway-us-west1-c.discord.gg"
    ]
    
    for gateway in gateways:
        result = resolve_gateway_fallback(gateway)
        if result:
            print(f"✅ {gateway} -> {result}")
        else:
            print(f"❌ {gateway} -> FAILED")
            # Try alternative DNS
            alt_result = test_alternative_dns(gateway)
            if alt_result:
                print(f"✅ {gateway} -> {alt_result} (via nslookup)")
    
    print("\nConnectivity testing complete!")