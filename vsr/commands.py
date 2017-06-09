import time

with open("send-commands.txt", "r+") as file:
    for line in file.readlines():
        print line
        time.sleep(0.1)
