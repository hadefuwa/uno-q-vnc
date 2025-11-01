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

    # Check current display resolution
    print("Checking current display resolution...")
    status, output, error = run_command(client, "DISPLAY=:0 xrandr", show_output=False)
    print(output)
    print()

    # Ask user what resolution they want or set a good default
    print("Setting display resolution to 1920x1080...")

    # Try to set resolution using xrandr
    status, output, error = run_command(client, "DISPLAY=:0 xrandr --output HDMI-1 --mode 1920x1080 2>/dev/null || DISPLAY=:0 xrandr --output HDMI-0 --mode 1920x1080 2>/dev/null || DISPLAY=:0 xrandr --output Virtual-1 --mode 1920x1080 2>/dev/null || echo 'Could not set via xrandr'", show_output=False)

    if "Could not set" in output:
        print("xrandr method didn't work, trying alternative approach...")

        # Get the output name
        status, outputs, error = run_command(client, "DISPLAY=:0 xrandr | grep ' connected' | awk '{print $1}'", show_output=False)

        if outputs:
            output_name = outputs.split('\n')[0]
            print(f"Found display output: {output_name}")

            # Add custom resolution
            print("Adding custom 1920x1080 mode...")
            run_command(client, "DISPLAY=:0 xrandr --newmode \"1920x1080_60.00\"  173.00  1920 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync", show_output=False)
            run_command(client, f"DISPLAY=:0 xrandr --addmode {output_name} 1920x1080_60.00", show_output=False)
            run_command(client, f"DISPLAY=:0 xrandr --output {output_name} --mode 1920x1080_60.00", show_output=False)
            print("✓ Resolution set to 1920x1080")
        else:
            print("⚠ Could not determine output name")
    else:
        print("✓ Resolution set to 1920x1080")

    # Alternative: Update the x11vnc service to clip/scale properly
    print("\nUpdating VNC service with resolution settings...")

    service_content = """[Unit]
Description=X11VNC Remote Desktop
After=graphical.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/arduino/.Xauthority"
ExecStart=/usr/bin/x11vnc -display :0 -auth /home/arduino/.Xauthority -forever -loop -noxdamage -repeat -rfbauth /home/arduino/.vnc/passwd -rfbport 5900 -shared -bg -ncache 10 -noscr
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

    # Restart VNC
    print("Restarting VNC service...")
    run_command(client, "systemctl daemon-reload", use_sudo=True, show_output=False)
    run_command(client, "systemctl restart x11vnc.service", use_sudo=True, show_output=False)

    time.sleep(2)

    print("✓ VNC server restarted with new settings\n")

    # Show current resolution
    print("Current display configuration:")
    status, output, error = run_command(client, "DISPLAY=:0 xrandr | grep -E 'connected|\\*'", show_output=False)
    print(output)

    print(f"\n🎉 Resolution updated! Reconnect your VNC viewer to {host}")
    print("\nNote: If the resolution still looks wrong, disconnect and reconnect your VNC viewer.")

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
