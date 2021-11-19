#!/usr/bin/env python3
#####################################################################################################
# Automated testing of Watiba class functions.  Pre-compiler not tested here.
#
# Author: Ray Walker
# raythonic@mgail.com
#####################################################################################################

import watiba as watiba
import sys

print("Running Smoke Test")

print("Instantiating Watiba")
w = watiba.Watiba()

print("Testing basic shell command execution")
o = w.bash('echo "success 2>&1"', True)
if o.exit_code != 0:
    print(f"ERROR: error on simple echo command: {o.exit_code}")
    sys.exit(1)

if o.stdout[0].strip() != "success 2>&1":
    print(f"ERROR: error on simple echo command.  STDOUT should say 'success': {o.stdout[0]}")
    sys.exit(1)

print("Basic shell execution passed.\n\n")

##########################################################################################################
print("Testing remote execution")
host = input("On which server should this run (Default: localhost)?")
if host == "":
    host = "localhost"

o = w.ssh('echo "success 2>&1"', host, port=32)
if o.exit_code != 0:
    print(f"ERROR: error on simple SSH echo command on host {host}: {o.exit_code}")
    sys.exit(1)

if o.stdout[0].strip() != "success":
    print(f"ERROR: error on simple SSH echo command on host {host}.  STDOUT should say 'success', but says: {o.stdout[0]}")
    sys.exit(1)

print("Remote shell execution passed.\n\n")

##########################################################################################################
print("Testing simple spawn and resolver callback")


def resolver1(promise, args):
    if "arg1" not in args:
        print(f"ERROR: Resolver called for spawn, but arguments not found.  Args: {args}")
        sys.exit(1)
    print("Resolver successfully called with args")
    return True


p = w.spawn('echo "success"', resolver1, {"arg1": "argument"})


try:
    p.join()
    if p.output.stdout[0] != "success":
        print(f"ERROR: Spawned command failed.  {p.command}")
        print(f"ERROR: Command's expected output incorrect.  {p.output.stdout[0]}")
        sys.exit(1)
except Exception as ex:
    print("ERROR: Exception thrown on promise join")
    sys.exit(1)
print("Simple spawn passed.\n\n")

##########################################################################################################
print("Testing remote spawn and resolver callback")


def resolver2(promise, args):
    if "arg1" not in args:
        print(f"ERROR: Resolver called for spawn, but arguments not found.  Args: {args}")
        sys.exit(1)
    print("Resolver successfully called with args")
    return True


p = w.spawn('echo "success"', resolver2, {"arg1": "argument"})


try:
    p.join()
    if p.output.stdout[0] != "success":
        print(f"ERROR: Spawned command failed.  {p.command}")
        print(f"ERROR: Command's expected output incorrect.  {p.output.stdout[0]}")
        sys.exit(1)
except Exception as ex:
    print("ERROR: Exception thrown on promise join")
    sys.exit(1)
print("Remote spawn passed.\n\n")

##########################################################################################################
print("Testing directory context")

o = w.bash("cd /tmp", context=True)

if o.cwd != "/tmp":
    print(f"ERROR: context was lost")
    sys.exit(1)
w.bash("cd ..", context=True)
print("Directory context passed.\n\n")

##########################################################################################################
print("Testing losing directory context")

# Make sure we are in /tmp as we don't want to write somewhere else
w.bash("cd /tmp", context=False)

# We should NOT have kept context
if o.cwd == "/tmp":
    print(f"ERROR: context should have been lost, but wasn't.")
    sys.exit(1)
w.bash("cd ..")
print("Losing directory context passed.\n\n")