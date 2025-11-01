#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import socket
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

host = "192.168.0.125"
username = "root"
password = "ummah123"

print(f"Testing connection to {host}...")

# First, test if the host is reachable
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((host, 22))
    sock.close()

    if result == 0:
        print("✓ Port 22 is open")
    else:
        print("✗ Port 22 is not reachable")
        exit(1)
except Exception as e:
    print(f"✗ Connection test failed: {e}")
    exit(1)

# Try different authentication methods
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Try with password authentication
try:
    print(f"\nAttempting SSH connection as {username}...")
    client.connect(
        host,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        auth_timeout=10,
        banner_timeout=10
    )
    print("✓ SSH connection successful!")

    # Test a simple command
    stdin, stdout, stderr = client.exec_command("whoami")
    result = stdout.read().decode().strip()
    print(f"✓ Command test successful. Logged in as: {result}")

    client.close()
except paramiko.AuthenticationException as e:
    print(f"✗ Authentication failed: {e}")
    print("\nPlease verify:")
    print("1. Username is correct (root)")
    print("2. Password is correct")
    print("3. Password authentication is enabled on the server")
except Exception as e:
    print(f"✗ Connection failed: {e}")
