#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

host = "192.168.0.125"
password = "ummah123"
possible_usernames = ["root", "pi", "arduino", "debian", "admin", "user"]

for username in possible_usernames:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Trying username: {username}... ", end='')
        client.connect(
            host,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            auth_timeout=5,
            banner_timeout=5
        )
        print("✓ SUCCESS!")

        # Get system info
        stdin, stdout, stderr = client.exec_command("whoami && uname -a")
        result = stdout.read().decode().strip()
        print(f"\nConnection details:")
        print(result)

        client.close()
        print(f"\n*** Use username '{username}' for SSH connection ***")
        exit(0)

    except paramiko.AuthenticationException:
        print("✗ Authentication failed")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        try:
            client.close()
        except:
            pass

print("\n*** Could not authenticate with any common username ***")
print("Please verify the correct username and password for your device.")
