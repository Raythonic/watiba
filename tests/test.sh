#!/bin/bash
cd /home/rwalk/git/watiba
bin/build.sh
echo "Version $(cat version.conf) built."

echo "Generating test Watiba examples in tmp/watiba_examples.py for build $(cat version.conf)"
echo "Generating Watiba smoketest to tmp/watiba_smoke_test.py $(cat version.conf)"
# Compile the examples
bin/compile.sh