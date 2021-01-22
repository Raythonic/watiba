#!/bin/bash
cd ~/git/watiba
# Compile the examples
if [ ! -d tmp ]
then
  mkdir tmp
fi

print("___________________________________________________________________________")
print("Running smoke test against Watiba class functions")
print("___________________________________________________________________________")
test/smoke_test1.py

echo "Compiling examples.wt and integrated_test1.wt"
~/.local/bin/watiba-c examples/examples.wt > tmp/watiba_examples.py
~/.local/bin/watiba-c tests/integrated_test1.wt > tmp/integrated_test1ntegrated_test1.py
chmod +x tmp/watiba_*.py
pushd tmp
print("___________________________________________________________________________")
print("Running examples")
print("___________________________________________________________________________")
./watiba_examples.py

print("___________________________________________________________________________")
print("Running Integration Test 1")
print("___________________________________________________________________________")
./integrated_test1.py
popd
