#!/bin/bash
cd ~/git/watiba

# Compile the examples
if [ ! -d tmp ]
then
  mkdir tmp
fi

echo "___________________________________________________________________________"
echo "Running smoke test against Watiba class functions"
echo "___________________________________________________________________________"
test/smoke_test1.py

echo "Compiling examples.wt and integrated_test1.wt"
~/.local/bin/watiba-c examples/examples.wt > tmp/watiba_examples.py
~/.local/bin/watiba-c tests/integrated_test1.wt > tmp/integrated_test1ntegrated_test1.py
chmod +x tmp/watiba_*.py

pushd tmp
echo "___________________________________________________________________________"
echo "Running examples"
echo "___________________________________________________________________________"
./watiba_examples.py

echo "___________________________________________________________________________"
echo "Running Integration Test 1"
echo "___________________________________________________________________________"
./integrated_test1.py
popd
