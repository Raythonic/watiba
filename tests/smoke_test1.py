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
print("Testing remote execution on localhost")
o = w.ssh('echo "success 2>&1"', "localhost", port=32)
if o.exit_code != 0:
    print(f"ERROR: error on simple SSH echo command: {o.exit_code}")
    sys.exit(1)

if o.stdout[0].strip() != "success":
    print(f"ERROR: error on simple SSH echo command.  STDOUT should say 'success': {o.stdout[0]}")
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

w.bash("cd tmp", True)
w.bash("touch fake_watiba_file.txt", True)
o = w.bash("ls fake_watiba_file.txt 2> /dev/null | wc -l", True)
if int(o.stdout[0]) == 1:
    w.bash("rm fake_watiba_file.ext", True)
else:
    print(f"ERROR: context was lost")
    sys.exit(1)
w.bash("cd ..")
print("Directory context passed.\n\n")

##########################################################################################################
print("Testing losing directory context")

# Make sure we are in /tmp as we don't want to write somewhere else
w.bash("cd tmp", True)

# Now setup the test
w.bash("mkdir watiba_dir && cd watiba_dir && touch fake_watiba_file.txt", False)

# We should NOT have kept context
o = w.bash("ls fake_watiba_file.txt 2> /dev/null | wc -l", False)
if int(o.stdout[0]) < 1:
    w.bash("rm fake_watiba_file.ext", False)
    w.bash("rm -r watiba_dir", False)
else:
    print(f"ERROR: context should have been lost, but wasn't.")
    sys.exit(1)
w.bash("cd ..")
print("Losing directory context passed.\n\n")