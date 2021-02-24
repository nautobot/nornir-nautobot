"""A set of helper utilities."""

import errno
import os
import logging
import socket

LOGGER = logging.getLogger(__name__)


def make_folder(folder):
    """Helper method to sanely create folders."""
    if not os.path.exists(folder):
        # Still try and except, since their may be race conditions.
        try:
            os.makedirs(folder)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


def hostname_resolves(hostname):
    """Helper method to check if IP resolves."""
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def test_tcp_port(ip_addr, port):
    """Helper method to 'ping' tcp port."""
    sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sckt.connect((ip_addr, int(port)))
        sckt.shutdown(1)
        return True
    except socket.error:
        return False


def is_ip(addr):
    """Helper method to check is string is an IP or not."""
    try:
        socket.inet_aton(addr)
        return True
    except socket.error:
        return False
