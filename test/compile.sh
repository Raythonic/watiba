#!/bin/bash

# Compile the examples
if [ ! -d tmp ]
then
  mkdir tmp
fi

~/.local/bin/watiba-c examples/examples.wt > tmp/watiba_examples.py
~/.local/bin/watiba-c test/smoke_test.wt > tmp/watiba_smoke_test.py
chmod +x tmp/watiba_*.py
