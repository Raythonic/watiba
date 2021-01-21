#!/bin/python3
import os

# This module will produce a new version.conf file
if not os.path.exists("version.conf"):
    with open("version.conf", "w") as f:
        print("0.0.0", file=f)

# Get the old version number and increment it
with open("version.conf", "r") as f:
    for v in f:
        ver = v.split(".")
        rel = int(ver[2]) + 1
        new_ver = f"{ver[0]}.{ver[1]}.{rel}"

with open("version.conf", "w") as f:
    f.write(new_ver)

# Give the caller the new version
print(new_ver)
