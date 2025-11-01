#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connection details
host = "192.168.0.125"
username = "arduino"
password = "ummah123"
public_key = """ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDRx3pDxboLWIwsDuVtGWVKBgv4tAZAR4PVe7PEUyEK4uJO8yaS9cmMOWYsvjhZvk/MnKqeRSni4tpPkYHTvQdUjTf/m7YvkKWWXnyD38FKc/8f9CecJEWa8tLt4882mmIRAH2iFStJ/M/j7iBQtp8nmhZT5s2CJ6gPuDgd/S8VazlSBfbXHC44N0glkYydy3sHaTa0S1+r1twXrlTdlx3i0zSaaFGHkB0JGzd+6Wyh2lNUh/nLLz7eYTkR6l73Iq8RJePaVrFmmOKd8tJAHT68ekciG/wHigia1/RSsUAFUKL887/AyRQMwpLBI8zrTfX7TmybiF5JgVi7PKfFNVQyjBCw/LhCbq3uq6QU9zSyFIYNulslbcob6MHyB/KeaY7q9CvVn5bl12vaGBpjd/Jkhj7ZN3f8EJvGlhQEiIusrsgPv5lcWG9O7FNxaGcU+sq7w0j9x82lmbT95aWlLP3iIlll85Ozy6VB9YY7pZppbSnPysN4v/g+Znb+bMhGOBBZKgUR8KAYzdVyRtVEcBZYpyZePwpjLX0pInpJqce/xF9omMZp+AXYMnlb9su9EVXWNCuEFtMobn3MUUQRhMXCvSQOZMFNlA2JfrJfo5BFUe07H5T34KPnwo4wIiNVut6ghjyp8ax9Zgay8SvQOejNozubot61MVuTRn87lFanBQ== Admin@Hamed-Down"""

try:
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect with password
    print(f"Connecting to {host}...")
    client.connect(host, username=username, password=password, look_for_keys=False, allow_agent=False)

    # Create .ssh directory if it doesn't exist
    print("Setting up .ssh directory...")
    stdin, stdout, stderr = client.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    stdout.channel.recv_exit_status()

    # Add public key to authorized_keys
    print("Adding public key to authorized_keys...")
    command = f'echo "{public_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()

    if exit_status == 0:
        print("✓ SSH key successfully copied!")
        print("You can now SSH without a password: ssh root@192.168.0.125")
    else:
        print(f"Error: {stderr.read().decode()}")
        sys.exit(1)

    client.close()

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
