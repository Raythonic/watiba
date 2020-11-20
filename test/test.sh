#!/bin/bash
cd /home/rwalk/git/watiba
echo "Building Watiba"
bin/build.sh

echo "Testing Watiba"
bin/watiba-c.py test/examples.wt > tmp/watiba_test.py
chmod +x tmp/watiba_test.py