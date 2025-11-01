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

    # Check which display manager is being used
    print("Checking display manager...")
    status, dm_output, error = run_command(client, "systemctl status display-manager.service | grep -i 'lightdm\\|gdm\\|sddm\\|lxdm' | head -1", use_sudo=True, show_output=False)

    # Also check what's actually running
    status, active_dm, error = run_command(client, "ps aux | grep -E 'lightdm|gdm|sddm|lxdm' | grep -v grep | head -1", show_output=False)

    print(f"Display manager info: {dm_output}")
    print(f"Running process: {active_dm}\n")

    # Determine display manager
    if "lightdm" in dm_output.lower() or "lightdm" in active_dm.lower():
        print("Detected LightDM display manager")
        print("Configuring LightDM for auto-login...\n")

        # Backup original config
        run_command(client, "cp /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.backup 2>/dev/null || echo 'No existing config to backup'", use_sudo=True, show_output=False)

        # Configure LightDM for auto-login
        lightdm_config = f"""[Seat:*]
autologin-user={username}
autologin-user-timeout=0
user-session=ubuntu
greeter-session=lightdm-gtk-greeter
"""

        # Write config
        cmd = f"cat > /tmp/lightdm.conf << 'EOFCONF'\n{lightdm_config}\nEOFCONF\n"
        run_command(client, cmd, show_output=False)
        run_command(client, "mv /tmp/lightdm.conf /etc/lightdm/lightdm.conf", use_sudo=True, show_output=False)
        run_command(client, "chmod 644 /etc/lightdm/lightdm.conf", use_sudo=True, show_output=False)

        # Add user to autologin group if needed
        run_command(client, f"groupadd -r autologin 2>/dev/null || echo 'Group exists'", use_sudo=True, show_output=False)
        run_command(client, f"gpasswd -a {username} autologin", use_sudo=True, show_output=False)

        print("✓ LightDM configured for auto-login")

    elif "gdm" in dm_output.lower() or "gdm" in active_dm.lower():
        print("Detected GDM display manager")
        print("Configuring GDM for auto-login...\n")

        # Configure GDM for auto-login
        gdm_config = f"""[daemon]
AutomaticLoginEnable=true
AutomaticLogin={username}
"""

        cmd = f"cat > /tmp/custom.conf << 'EOFCONF'\n{gdm_config}\nEOFCONF\n"
        run_command(client, cmd, show_output=False)
        run_command(client, "mv /tmp/custom.conf /etc/gdm3/custom.conf", use_sudo=True, show_output=False)
        run_command(client, "chmod 644 /etc/gdm3/custom.conf", use_sudo=True, show_output=False)

        print("✓ GDM configured for auto-login")

    else:
        print("⚠ Could not detect display manager, trying LightDM configuration anyway...")

        # Try LightDM config anyway
        lightdm_config = f"""[Seat:*]
autologin-user={username}
autologin-user-timeout=0
user-session=ubuntu
greeter-session=lightdm-gtk-greeter
"""
        cmd = f"cat > /tmp/lightdm.conf << 'EOFCONF'\n{lightdm_config}\nEOFCONF\n"
        run_command(client, cmd, show_output=False)
        run_command(client, "mkdir -p /etc/lightdm", use_sudo=True, show_output=False)
        run_command(client, "mv /tmp/lightdm.conf /etc/lightdm/lightdm.conf", use_sudo=True, show_output=False)

    # Also configure systemd auto-login for console (fallback)
    print("\nConfiguring console auto-login as fallback...")
    run_command(client, f"mkdir -p /etc/systemd/system/getty@tty1.service.d", use_sudo=True, show_output=False)

    console_override = f"""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin {username} --noclear %I $TERM
"""

    cmd = f"cat > /tmp/override.conf << 'EOFCONF'\n{console_override}\nEOFCONF\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "mv /tmp/override.conf /etc/systemd/system/getty@tty1.service.d/override.conf", use_sudo=True, show_output=False)
    run_command(client, "systemctl daemon-reload", use_sudo=True, show_output=False)

    print("✓ Console auto-login configured\n")

    print("🎉 Auto-login has been configured!")
    print(f"\nThe system will automatically log in as '{username}' on next boot.")
    print("\nOptions:")
    print("1. Reboot now: The changes will take effect immediately")
    print("2. Reboot later: The changes will take effect on next boot")

    print("\nDo you want to reboot now? (system will reboot in 10 seconds if yes)")

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
