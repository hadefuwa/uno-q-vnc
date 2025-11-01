# Arduino Uno Q Setup Guide

This guide will help you set up your Arduino Uno Q (Debian-based) with VNC server, auto-login, and disabled power management.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Step 1: Install and Configure VNC Server](#step-1-install-and-configure-vnc-server)
- [Step 2: Enable Auto-Login](#step-2-enable-auto-login)
- [Step 3: Disable Screensaver and Sleep Modes](#step-3-disable-screensaver-and-sleep-modes)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## Prerequisites

### What You Need
- Arduino Uno Q running Debian Linux
- Network connection (Arduino connected to your local network)
- IP address of your Arduino (e.g., `192.168.0.125`)
- Username and password for your Arduino
  - Default username is often `arduino` (NOT `root`)
  - You should know your password

### On Your Computer
- **Windows**: Python 3 installed
- **Linux/Mac**: SSH client (usually pre-installed)
- **VNC Viewer**: Download from [RealVNC](https://www.realvnc.com/en/connect/download/viewer/)

### Finding Your Arduino's Username
If you're not sure of the username, try these common ones:
- `arduino`
- `pi`
- `debian`
- `root`

You can test by SSHing: `ssh username@IP_ADDRESS`

---

## Step 1: Install and Configure VNC Server

VNC allows you to remotely view and control the Arduino's desktop.

### 1.1 Install x11vnc

SSH into your Arduino:
```bash
ssh arduino@192.168.0.125
```

Install x11vnc:
```bash
sudo apt update
sudo apt install -y x11vnc
```

### 1.2 Set VNC Password

Create a password file for VNC:
```bash
mkdir -p ~/.vnc
x11vnc -storepasswd YOUR_PASSWORD ~/.vnc/passwd
```

Replace `YOUR_PASSWORD` with your desired VNC password.

### 1.3 Create VNC Service

Create a systemd service to auto-start VNC on boot:

```bash
sudo nano /etc/systemd/system/x11vnc.service
```

Paste this content (press Ctrl+Shift+V to paste):

```ini
[Unit]
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
```

**Note:** Replace `arduino` with your actual username if different.

Save and exit (Ctrl+X, then Y, then Enter).

### 1.4 Enable and Start VNC Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable x11vnc.service
sudo systemctl start x11vnc.service
```

### 1.5 Verify VNC is Running

Check the service status:
```bash
sudo systemctl status x11vnc.service
```

Check if port 5900 is listening:
```bash
ss -tlnp | grep 5900
```

You should see x11vnc listening on port 5900.

### 1.6 Connect with VNC Viewer

1. Open **RealVNC Viewer** on your computer
2. Enter the Arduino's IP address: `192.168.0.125` (or just `192.168.0.125:5900`)
3. When warned about encryption:
   - Click **Continue** or
   - Go to File → Preferences → Expert → Set "Encryption" to "PreferOff"
4. Enter your VNC password when prompted
5. You should now see the Arduino's desktop!

---

## Step 2: Enable Auto-Login

Configure the Arduino to automatically log in without requiring a password at boot.

### 2.1 Configure LightDM (Display Manager)

SSH into your Arduino:
```bash
ssh arduino@192.168.0.125
```

Edit the LightDM configuration:
```bash
sudo nano /etc/lightdm/lightdm.conf
```

Add or modify these lines under `[Seat:*]`:
```ini
[Seat:*]
autologin-user=arduino
autologin-user-timeout=0
user-session=ubuntu
greeter-session=lightdm-gtk-greeter
```

Save and exit (Ctrl+X, then Y, then Enter).

### 2.2 Add User to Autologin Group

```bash
sudo groupadd -r autologin 2>/dev/null
sudo gpasswd -a arduino autologin
```

### 2.3 Configure Console Auto-Login (Optional)

This ensures auto-login even if the display manager fails:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
```

Paste this content:
```ini
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin arduino --noclear %I $TERM
```

Save and exit.

Reload systemd:
```bash
sudo systemctl daemon-reload
```

### 2.4 Reboot and Test

```bash
sudo reboot
```

After reboot, the system should automatically log in as `arduino` without prompting for a password.

---

## Step 3: Disable Screensaver and Sleep Modes

Prevent the Arduino from sleeping or turning off the display.

### 3.1 Disable X11 Screensaver

SSH into your Arduino:
```bash
ssh arduino@192.168.0.125
```

Run these commands:
```bash
DISPLAY=:0 xset s off
DISPLAY=:0 xset s noblank
DISPLAY=:0 xset -dpms
```

### 3.2 Make Screensaver Settings Persistent

Create an autostart script:
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/disable-screensaver.desktop
```

Paste this content:
```ini
[Desktop Entry]
Type=Application
Name=Disable Screensaver
Exec=sh -c "xset s off; xset s noblank; xset -dpms"
X-GNOME-Autostart-enabled=true
```

Save and exit.

Make it executable:
```bash
chmod +x ~/.config/autostart/disable-screensaver.desktop
```

### 3.3 Configure LightDM to Disable Screensaver

```bash
sudo mkdir -p /etc/lightdm/lightdm.conf.d
sudo nano /etc/lightdm/lightdm.conf.d/50-no-screensaver.conf
```

Paste this content:
```ini
[SeatDefaults]
xserver-command=X -s 0 -dpms
```

Save and exit.

### 3.4 Disable System Sleep/Suspend/Hibernate

```bash
sudo systemctl mask sleep.target
sudo systemctl mask suspend.target
sudo systemctl mask hibernate.target
sudo systemctl mask hybrid-sleep.target
```

### 3.5 Disable XFCE Power Management (if using XFCE)

```bash
DISPLAY=:0 xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/blank-on-ac -s 0
DISPLAY=:0 xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/dpms-enabled -s false
DISPLAY=:0 xfconf-query -c xfce4-screensaver -p /saver/enabled -s false
```

### 3.6 Create System-Wide Init Script

Create a script that runs on boot:
```bash
sudo nano /usr/local/bin/disable-screensaver.sh
```

Paste this content:
```bash
#!/bin/bash
# Disable screensaver and power management
export DISPLAY=:0
xset s off
xset s noblank
xset -dpms
```

Save and make executable:
```bash
sudo chmod +x /usr/local/bin/disable-screensaver.sh
```

Create a systemd service:
```bash
sudo nano /etc/systemd/system/disable-screensaver.service
```

Paste this content:
```ini
[Unit]
Description=Disable Screensaver and Power Management
After=graphical.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/disable-screensaver.sh
RemainAfterExit=yes

[Install]
WantedBy=graphical.target
```

Enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable disable-screensaver.service
sudo systemctl start disable-screensaver.service
```

### 3.7 Verify Settings

Check that screensaver is disabled:
```bash
DISPLAY=:0 xset q | grep -A 5 "Screen Saver"
```

You should see:
- `timeout: 0` (screensaver disabled)
- `DPMS is Disabled` (power management off)

---

## Troubleshooting

### VNC Issues

**Problem:** "Connection refused" when connecting to VNC
- **Solution:** Check if x11vnc is running:
  ```bash
  sudo systemctl status x11vnc.service
  ps aux | grep x11vnc
  ```
  Restart if needed:
  ```bash
  sudo systemctl restart x11vnc.service
  ```

**Problem:** VNC shows "Unencrypted connection" warning
- **Solution:** This is normal. Click "Continue" or change RealVNC settings:
  - File → Preferences → Expert
  - Set "Encryption" to "PreferOff" or "AlwaysOff"

**Problem:** VNC shows a weird/wrong resolution
- **Solution:** Check the display resolution on the Arduino:
  ```bash
  DISPLAY=:0 xrandr
  ```
  Set to desired resolution (e.g., 1920x1080):
  ```bash
  DISPLAY=:0 xrandr --output DP-1 --mode 1920x1080
  ```

**Problem:** Can't find the correct display output name
- **Solution:** List connected displays:
  ```bash
  DISPLAY=:0 xrandr | grep " connected"
  ```

### Auto-Login Issues

**Problem:** System still asks for password on boot
- **Solution:**
  - Verify LightDM configuration: `cat /etc/lightdm/lightdm.conf`
  - Check that the username is correct
  - Make sure you added the user to the autologin group

### Screensaver/Sleep Issues

**Problem:** Screen still turns off or blanks
- **Solution:**
  - Run the xset commands again manually
  - Check if screensaver service is running and enabled
  - Verify DPMS is disabled: `DISPLAY=:0 xset q`

**Problem:** System still goes to sleep
- **Solution:** Check that sleep targets are masked:
  ```bash
  systemctl status sleep.target
  systemctl status suspend.target
  ```

---

## Quick Reference

### Essential Commands

**SSH into Arduino:**
```bash
ssh arduino@192.168.0.125
```

**Restart VNC service:**
```bash
sudo systemctl restart x11vnc.service
```

**Check VNC status:**
```bash
sudo systemctl status x11vnc.service
```

**Disable screensaver manually:**
```bash
DISPLAY=:0 xset s off && DISPLAY=:0 xset s noblank && DISPLAY=:0 xset -dpms
```

**Reboot Arduino:**
```bash
sudo reboot
```

**Shutdown Arduino:**
```bash
sudo shutdown -h now
```

### Important File Locations

| Purpose | File Path |
|---------|-----------|
| VNC password | `~/.vnc/passwd` |
| VNC service | `/etc/systemd/system/x11vnc.service` |
| LightDM config | `/etc/lightdm/lightdm.conf` |
| Auto-login config | `/etc/lightdm/lightdm.conf.d/` |
| Screensaver disable script | `/usr/local/bin/disable-screensaver.sh` |

### Default Settings Used in This Guide

| Setting | Value |
|---------|-------|
| Arduino IP | `192.168.0.125` |
| Username | `arduino` |
| VNC Port | `5900` |
| SSH Port | `22` |
| Display | `:0` |

**Remember to replace these values with your actual settings!**

---

## Summary

After following this guide, your Arduino Uno Q will:

- ✅ Run a VNC server on port 5900 (accessible via RealVNC Viewer)
- ✅ Automatically log in on boot (no password prompt)
- ✅ Never sleep, suspend, or turn off the display
- ✅ All services start automatically on boot

### Next Steps

- Set up firewall rules if needed
- Configure static IP address for the Arduino
- Set up additional services or applications
- Create backups of important configuration files

---

## Additional Resources

- [Arduino Official Documentation](https://www.arduino.cc/)
- [Debian Documentation](https://www.debian.org/doc/)
- [x11vnc Documentation](https://github.com/LibVNC/x11vnc)
- [OpenSSH Documentation](https://www.openssh.com/manual.html)
- [RealVNC Viewer Download](https://www.realvnc.com/en/connect/download/viewer/)

---

**Created:** 2025-11-01
**Last Updated:** 2025-11-01
**Tested On:** Arduino Uno Q (Debian, Linux kernel 6.16.7)
