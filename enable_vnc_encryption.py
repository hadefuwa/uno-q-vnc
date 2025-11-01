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

    # Generate self-signed certificate
    print("Generating SSL certificate...")
    run_command(client, "mkdir -p ~/.vnc", show_output=False)
    cert_cmd = "openssl req -new -x509 -days 365 -nodes -out ~/.vnc/server.pem -keyout ~/.vnc/server.pem -subj '/C=US/ST=State/L=City/O=Home/CN=arduino'"
    run_command(client, cert_cmd, show_output=False)
    run_command(client, "chmod 600 ~/.vnc/server.pem", show_output=False)
    print("✓ Certificate generated\n")

    # Update systemd service with SSL support
    print("Updating VNC service with encryption...")
    service_content = """[Unit]
Description=X11VNC Remote Desktop with SSL
After=graphical.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/arduino/.Xauthority"
ExecStart=/usr/bin/x11vnc -display :0 -auth /home/arduino/.Xauthority -forever -loop -noxdamage -repeat -rfbauth /home/arduino/.vnc/passwd -rfbport 5900 -shared -ssl /home/arduino/.vnc/server.pem -bg
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
        print("✓ Encrypted VNC server is running!\n")
        print("🎉 VNC server now has SSL/TLS encryption enabled!")
        print(f"\nConnection details:")
        print(f"  Host: {host}")
        print(f"  Port: 5900")
        print(f"  Password: {password}")
        print(f"  Encryption: SSL/TLS (self-signed certificate)")
        print(f"\nNote: You may need to accept the self-signed certificate in RealVNC Viewer")
    else:
        print(f"⚠ Service status: {output}")
        run_command(client, "journalctl -u x11vnc.service -n 20 --no-pager", use_sudo=True)

    # Check port
    print("\nVerifying port 5900...")
    status, output, error = run_command(client, "ss -tlnp | grep 5900", use_sudo=True, show_output=False)
    if output:
        print(f"✓ Listening:\n{output}")

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
