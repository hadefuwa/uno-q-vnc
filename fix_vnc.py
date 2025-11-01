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
    if show_output and error:
        print(f"Error: {error}")

    return exit_status, output, error

try:
    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, look_for_keys=False, allow_agent=False)
    print("✓ Connected\n")

    # Check if x11vnc is installed
    print("Checking x11vnc installation...")
    status, output, error = run_command(client, "which x11vnc", show_output=False)
    if status != 0:
        print("✗ x11vnc not found, installing...")
        run_command(client, "DEBIAN_FRONTEND=noninteractive apt install -y x11vnc", use_sudo=True)
    else:
        print(f"✓ x11vnc found at: {output}\n")

    # Check what display server is running
    print("Checking display server...")
    status, output, error = run_command(client, "echo $DISPLAY", show_output=False)
    print(f"DISPLAY variable: {output if output else '(not set)'}")

    status, output, error = run_command(client, "ps aux | grep -E 'X|Xorg|wayland|weston' | grep -v grep", show_output=False)
    if output:
        print(f"Display processes:\n{output}\n")

    # Check for existing VNC servers
    print("Checking for existing VNC configuration...")
    status, output, error = run_command(client, "systemctl list-units --all '*vnc*' --no-pager", use_sudo=True, show_output=False)
    if output:
        print(f"VNC services found:\n{output}\n")

    # Check if vncserver-x11-serviced exists (RealVNC)
    status, output, error = run_command(client, "systemctl status vncserver-x11-serviced.service", use_sudo=True, show_output=False)
    if "could not be found" not in error and "not found" not in output:
        print("Found RealVNC server service!")
        print("Enabling and starting RealVNC server...")

        # Enable and start RealVNC
        run_command(client, "systemctl enable vncserver-x11-serviced.service", use_sudo=True, show_output=False)
        run_command(client, "systemctl start vncserver-x11-serviced.service", use_sudo=True, show_output=False)
        time.sleep(2)

        status, output, error = run_command(client, "systemctl is-active vncserver-x11-serviced.service", use_sudo=True, show_output=False)
        if "active" in output:
            print("✓ RealVNC server is now running!")
            print(f"\n🎉 VNC server successfully enabled!")
            print(f"\nConnection details:")
            print(f"  Host: {host}")
            print(f"  Port: 5900 (default VNC port)")
            print(f"\nConnect using RealVNC Viewer to: {host}")
        else:
            print(f"Status: {output}")
            print("\nChecking logs...")
            run_command(client, "journalctl -u vncserver-x11-serviced.service -n 30 --no-pager", use_sudo=True)
    else:
        print("RealVNC server service not found, using x11vnc instead...\n")

        # Remove broken service file
        print("Cleaning up old service file...")
        run_command(client, "rm -f /etc/systemd/system/x11vnc.service", use_sudo=True, show_output=False)

        # Create proper x11vnc service
        print("Creating x11vnc service...")
        service_content = """[Unit]
Description=X11VNC Remote Desktop
After=graphical.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/arduino/.Xauthority"
ExecStart=/usr/bin/x11vnc -display :0 -auth /home/arduino/.Xauthority -forever -loop -noxdamage -repeat -rfbauth /home/arduino/.vnc/passwd -rfbport 5900 -shared -bg
User=arduino
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical.target
"""

        # Write service file properly
        cmd = f"cat > /tmp/x11vnc.service << 'EOFSERVICE'\n{service_content}\nEOFSERVICE\n"
        run_command(client, cmd, show_output=False)
        run_command(client, "mv /tmp/x11vnc.service /etc/systemd/system/x11vnc.service", use_sudo=True, show_output=False)
        run_command(client, "chmod 644 /etc/systemd/system/x11vnc.service", use_sudo=True, show_output=False)

        # Set VNC password
        print("Setting VNC password...")
        run_command(client, "mkdir -p ~/.vnc", show_output=False)
        run_command(client, f"x11vnc -storepasswd {password} ~/.vnc/passwd", show_output=False)

        # Find correct X authority file
        print("Finding X authority...")
        status, xauth, error = run_command(client, "find /home/arduino -name '.Xauthority' 2>/dev/null | head -1", show_output=False)
        if not xauth:
            status, xauth, error = run_command(client, "find /run/user -name 'gdm' -o -name 'lightdm' 2>/dev/null", show_output=False)

        if xauth:
            print(f"Found X authority: {xauth}")

        # Reload and start
        print("Starting x11vnc service...")
        run_command(client, "systemctl daemon-reload", use_sudo=True, show_output=False)
        run_command(client, "systemctl enable x11vnc.service", use_sudo=True, show_output=False)
        run_command(client, "systemctl start x11vnc.service", use_sudo=True, show_output=False)

        time.sleep(2)
        status, output, error = run_command(client, "systemctl is-active x11vnc.service", use_sudo=True, show_output=False)

        if "active" in output:
            print("✓ x11vnc server is running!")
            print(f"\n🎉 VNC server successfully enabled!")
            print(f"\nConnection details:")
            print(f"  Host: {host}")
            print(f"  Port: 5900")
            print(f"  Password: {password}")
        else:
            print(f"⚠ Service status: {output}")
            print("\nTrying to start manually...")
            run_command(client, "DISPLAY=:0 x11vnc -auth ~/.Xauthority -forever -shared -rfbport 5900 -rfbauth ~/.vnc/passwd &", show_output=True)

    # Final check - see what's listening on port 5900
    print("\n" + "="*50)
    print("Checking what's listening on VNC port 5900...")
    status, output, error = run_command(client, "netstat -tlnp 2>/dev/null | grep 5900 || ss -tlnp | grep 5900", use_sudo=True, show_output=False)
    if output:
        print(f"✓ Port 5900 is listening:\n{output}")
    else:
        print("⚠ Nothing is listening on port 5900")
        print("\nTrying to start x11vnc manually in background...")
        run_command(client, "DISPLAY=:0 x11vnc -forever -shared -rfbport 5900 -rfbauth ~/.vnc/passwd -bg -o /tmp/x11vnc.log", show_output=True)
        time.sleep(2)
        status, output, error = run_command(client, "netstat -tlnp 2>/dev/null | grep 5900 || ss -tlnp | grep 5900", use_sudo=True, show_output=False)
        if output:
            print(f"✓ Now listening:\n{output}")
        else:
            print("Checking logs...")
            run_command(client, "cat /tmp/x11vnc.log 2>/dev/null || echo 'No log file'", show_output=True)

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
