#!/usr/bin/env python3

import sys

try:
    health_file = open("/health", "r")
    health = health_file.read()
    health_file.close()
except FileNotFoundError:
    print("health status file not found")
    sys.exit(2)

exit_status, message = health.strip().split(" ", 1)

if message != '':
    print(message)

sys.exit(int(exit_status))
