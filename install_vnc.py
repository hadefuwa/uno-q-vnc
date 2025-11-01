#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

host = "192.168.0.125"
username = "arduino"
password = "ummah123"

def run_command(client, command, use_sudo=False):
    """Run a command and return the output"""
    if use_sudo:
        # Use sudo with password from stdin
        command = f"echo '{password}' | sudo -S {command}"

    stdin, stdout, stderr = client.exec_command(command)

    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()

    output = stdout.read().decode('utf-8').strip()
    error = stderr.read().decode('utf-8').strip()

    return exit_status, output, error

try:
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, look_for_keys=False, allow_agent=False)
    print("✓ Connected")

    # Update package list
    print("\nUpdating package list...")
    status, output, error = run_command(client, "apt update", use_sudo=True)
    if status == 0:
        print("✓ Package list updated")
    else:
        print(f"✗ Update failed: {error}")

    # Install x11vnc
    print("\nInstalling x11vnc...")
    status, output, error = run_command(client, "DEBIAN_FRONTEND=noninteractive apt install -y x11vnc", use_sudo=True)
    if status == 0:
        print("✓ x11vnc installed")
    else:
        print(f"⚠ Installation output: {error}")

    # Set VNC password
    print("\nSetting VNC password...")
    status, output, error = run_command(client, f"mkdir -p ~/.vnc && x11vnc -storepasswd {password} ~/.vnc/passwd", use_sudo=False)
    if status == 0:
        print("✓ VNC password set")
    else:
        print(f"⚠ Password setup: {error}")

    # Create systemd service for x11vnc
    print("\nCreating systemd service...")
    service_content = """[Unit]
Description=X11VNC Remote Desktop
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/x11vnc -display :0 -auth guess -forever -loop -noxdamage -repeat -rfbauth /home/arduino/.vnc/passwd -rfbport 5900 -shared
User=arduino
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
"""

    # Write service file
    stdin, stdout, stderr = client.exec_command(f"echo '{password}' | sudo -S tee /etc/systemd/system/x11vnc.service > /dev/null")
    stdin.write(service_content)
    stdin.flush()
    stdin.channel.shutdown_write()
    stdout.channel.recv_exit_status()
    print("✓ Service file created")

    # Enable and start the service
    print("\nEnabling and starting VNC service...")
    status, output, error = run_command(client, "systemctl daemon-reload", use_sudo=True)
    status, output, error = run_command(client, "systemctl enable x11vnc.service", use_sudo=True)
    status, output, error = run_command(client, "systemctl start x11vnc.service", use_sudo=True)

    # Check service status
    time.sleep(2)
    status, output, error = run_command(client, "systemctl is-active x11vnc.service", use_sudo=True)

    if "active" in output:
        print("✓ VNC server is running")
        print(f"\n🎉 VNC server successfully enabled!")
        print(f"\nConnection details:")
        print(f"  Host: {host}")
        print(f"  Port: 5900")
        print(f"  Password: {password}")
        print(f"\nConnect using: vncviewer {host}:5900")
    else:
        print(f"⚠ Service status: {output}")
        print("\nChecking service logs...")
        status, output, error = run_command(client, "journalctl -u x11vnc.service -n 20 --no-pager", use_sudo=True)
        print(output)

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
