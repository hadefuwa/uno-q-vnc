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

    print("Disabling screensavers and sleep modes...\n")

    # 1. Disable X11 screensaver
    print("1. Disabling X11 screensaver...")
    run_command(client, "DISPLAY=:0 xset s off", show_output=False)
    run_command(client, "DISPLAY=:0 xset s noblank", show_output=False)
    run_command(client, "DISPLAY=:0 xset -dpms", show_output=False)
    print("✓ X11 screensaver and DPMS disabled")

    # 2. Make it persistent - create autostart script
    print("\n2. Creating autostart script for persistence...")
    run_command(client, "mkdir -p ~/.config/autostart", show_output=False)

    autostart_script = """[Desktop Entry]
Type=Application
Name=Disable Screensaver
Exec=sh -c "xset s off; xset s noblank; xset -dpms"
X-GNOME-Autostart-enabled=true
"""

    cmd = f"cat > ~/.config/autostart/disable-screensaver.desktop << 'EOFSCRIPT'\n{autostart_script}\nEOFSCRIPT\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "chmod +x ~/.config/autostart/disable-screensaver.desktop", show_output=False)
    print("✓ Autostart script created")

    # 3. Disable LightDM screensaver settings
    print("\n3. Configuring LightDM to disable screensaver...")
    lightdm_script = """[SeatDefaults]
xserver-command=X -s 0 -dpms
"""

    cmd = f"cat > /tmp/lightdm-no-screensaver.conf << 'EOFCONF'\n{lightdm_script}\nEOFCONF\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "mv /tmp/lightdm-no-screensaver.conf /etc/lightdm/lightdm.conf.d/50-no-screensaver.conf", use_sudo=True, show_output=False)
    print("✓ LightDM configured")

    # 4. Disable systemd sleep/suspend/hibernate
    print("\n4. Disabling system sleep, suspend, and hibernate...")
    sleep_targets = [
        "sleep.target",
        "suspend.target",
        "hibernate.target",
        "hybrid-sleep.target"
    ]

    for target in sleep_targets:
        run_command(client, f"systemctl mask {target}", use_sudo=True, show_output=False)

    print("✓ System sleep modes disabled")

    # 5. Disable idle actions
    print("\n5. Configuring power management...")

    # Check if using GNOME/MATE settings
    status, output, error = run_command(client, "which gsettings", show_output=False)
    if status == 0:
        print("   Configuring GNOME/MATE power settings...")
        gnome_commands = [
            "DISPLAY=:0 gsettings set org.gnome.desktop.screensaver idle-activation-enabled false",
            "DISPLAY=:0 gsettings set org.gnome.desktop.screensaver lock-enabled false",
            "DISPLAY=:0 gsettings set org.gnome.desktop.session idle-delay 0",
            "DISPLAY=:0 gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'",
            "DISPLAY=:0 gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'",
        ]
        for cmd in gnome_commands:
            run_command(client, cmd, show_output=False)
        print("   ✓ GNOME/MATE settings configured")

    # Check for XFCE
    status, output, error = run_command(client, "which xfconf-query", show_output=False)
    if status == 0:
        print("   Configuring XFCE power settings...")
        xfce_commands = [
            "DISPLAY=:0 xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/blank-on-ac -s 0",
            "DISPLAY=:0 xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/dpms-enabled -s false",
            "DISPLAY=:0 xfconf-query -c xfce4-screensaver -p /saver/enabled -s false",
        ]
        for cmd in xfce_commands:
            run_command(client, cmd, show_output=False)
        print("   ✓ XFCE settings configured")

    print("✓ Power management configured")

    # 6. Create a script to run on boot
    print("\n6. Creating system-wide init script...")
    boot_script = """#!/bin/bash
# Disable screensaver and power management
export DISPLAY=:0
xset s off
xset s noblank
xset -dpms
"""

    cmd = f"cat > /tmp/disable-screensaver.sh << 'EOFSCRIPT'\n{boot_script}\nEOFSCRIPT\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "mv /tmp/disable-screensaver.sh /usr/local/bin/disable-screensaver.sh", use_sudo=True, show_output=False)
    run_command(client, "chmod +x /usr/local/bin/disable-screensaver.sh", use_sudo=True, show_output=False)

    # Create systemd service for it
    systemd_service = """[Unit]
Description=Disable Screensaver and Power Management
After=graphical.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/disable-screensaver.sh
RemainAfterExit=yes

[Install]
WantedBy=graphical.target
"""

    cmd = f"cat > /tmp/disable-screensaver.service << 'EOFSERVICE'\n{systemd_service}\nEOFSERVICE\n"
    run_command(client, cmd, show_output=False)
    run_command(client, "mv /tmp/disable-screensaver.service /etc/systemd/system/disable-screensaver.service", use_sudo=True, show_output=False)
    run_command(client, "systemctl daemon-reload", use_sudo=True, show_output=False)
    run_command(client, "systemctl enable disable-screensaver.service", use_sudo=True, show_output=False)
    print("✓ System service created and enabled")

    # 7. Apply settings immediately
    print("\n7. Applying settings immediately...")
    run_command(client, "DISPLAY=:0 xset s off; DISPLAY=:0 xset s noblank; DISPLAY=:0 xset -dpms", show_output=False)
    print("✓ Settings applied")

    # 8. Verify current settings
    print("\n8. Verifying current settings...")
    status, output, error = run_command(client, "DISPLAY=:0 xset q | grep -A 5 'Screen Saver'", show_output=False)
    print(output)

    print("\n" + "="*60)
    print("🎉 Screensaver and sleep modes have been disabled!")
    print("="*60)
    print("\nWhat was disabled:")
    print("  ✓ X11 screensaver")
    print("  ✓ DPMS (Display Power Management)")
    print("  ✓ System sleep/suspend/hibernate")
    print("  ✓ Idle screen blanking")
    print("  ✓ Desktop environment power settings")
    print("\nThese settings will persist across reboots.")
    print("Your display will stay on indefinitely.")

    client.close()

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
