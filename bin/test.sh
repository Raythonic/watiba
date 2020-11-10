#!/bin/bash

echo "Testing Watiba"
../src/watiba-c.py ../test/test.wt > /tmp/watiba_test.py
chmod +x /tmp/watiba_test.py
/tmp/watiba_test.py