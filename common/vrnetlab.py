#!/usr/bin/env python3

class VR:
    def __init__(self):
        pass

    def update_health(self, exit_status, message):
        health_file = open("/health", "w")
        health_file.write("%d %s" % (exit_status, message))
        health_file.close()
