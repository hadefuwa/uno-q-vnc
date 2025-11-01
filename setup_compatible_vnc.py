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

def run_command(client, command, use_sudo=False, show_output=True):
    """Run a command and return the output"""
    if use_sudo:
        command = f"echo '{password}' | sudo -S {command}"

    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8').strip()
    error = stderr.read().decode('utf-8').strip()

    if show_output and output:
        print(output)
    if show_output and error and "sudo" not in error:
        print(f"Error: {error}")

    return exit_status, output, error

try:
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, look_for_keys=False, allow_agent=False)
    print("✓ Connected\n")

    print("Configuring x11vnc for RealVNC Viewer compatibility...")
    print("(Using unencrypted mode - fine for local network)\n")

    # Update systemd service WITHOUT SSL (RealVNC compatibility)
    service_content = """[Unit]
Description=X11VNC Remote Desktop
After=graphical.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/arduino/.Xauthority"
ExecStart=/usr/bin/x11vnc -display :0 -auth /home/arduino/.Xauthority -forever -loop -noxdamage -repeat -rfbauth /home/arduino/.vnc/passwd -rfbport 5900 -shared -bg -ncache 10
User=arduino
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical.target
"""

    # Write service file
    cmd = f"cat > /tmp/x11vnc.service << 'EOFSERVICE'\n{service_content}\nEOFSERVICE\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "mv /tmp/x11vnc.service /etc/systemd/system/x11vnc.service", use_sudo=True, show_output=False)
    run_command(client, "chmod 644 /etc/systemd/system/x11vnc.service", use_sudo=True, show_output=False)

    # Restart service
    print("Restarting VNC service...")
    run_command(client, "systemctl daemon-reload", use_sudo=True, show_output=False)
    run_command(client, "systemctl restart x11vnc.service", use_sudo=True, show_output=False)

    time.sleep(2)
    status, output, error = run_command(client, "systemctl is-active x11vnc.service", use_sudo=True, show_output=False)

    if "active" in output:
        print("✓ VNC server is running!\n")
        print("🎉 VNC server configured for RealVNC Viewer!")
        print(f"\nConnection details:")
        print(f"  Host: {host}")
        print(f"  Port: 5900 (or just use {host})")
        print(f"  Password: {password}")
        print(f"  Encryption: None (unencrypted - fine for local network)")
        print(f"\nIn RealVNC Viewer:")
        print(f"  1. When prompted about encryption, select 'Continue' or")
        print(f"     change encryption to 'Prefer off' or 'Always off' in settings")
        print(f"  2. Enter the password when prompted")
    else:
        print(f"⚠ Service status: {output}")
        print("\nTrying manual start...")
        run_command(client, "killall x11vnc 2>/dev/null", show_output=False)
        time.sleep(1)
        run_command(client, "DISPLAY=:0 x11vnc -auth /home/arduino/.Xauthority -forever -shared -rfbport 5900 -rfbauth /home/arduino/.vnc/passwd -bg -ncache 10", show_output=True)
        time.sleep(2)

    # Check port
    print("\nVerifying port 5900...")
    status, output, error = run_command(client, "ss -tlnp | grep 5900", use_sudo=True, show_output=False)
    if output:
        print(f"✓ Listening on port 5900:\n{output}")
    else:
        print("⚠ Not listening on port 5900")

    # Also check firewall
    print("\nChecking firewall...")
    status, output, error = run_command(client, "iptables -L INPUT -n | grep 5900 || echo 'No specific firewall rule (should be fine)'", use_sudo=True, show_output=False)
    print(output if output else "No firewall blocking VNC")

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
