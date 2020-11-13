#!/bin/python3
import os

if not os.path.exists("watiba/version.py"):
    with open("watiba/version", "w") as f:
        print("0.0.0", file=f)

new_ver = ""
with open("watiba/version.py", "r") as f:
    for v in f:
        ver = v.split(".")
        rel = int(ver[2]) + 1
        new_ver = "{}.{}.{}".format(ver[0], ver[1], rel)

with open("watiba/version.py", "w") as f:
    f.write(new_ver)

print(new_ver)
