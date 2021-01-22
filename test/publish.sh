#!/bin/bash
cd ~/git/watiba
test/build.sh
ver=$(cat version.conf)
echo "Build of ${ver} successful"

echo ""
echo "Pushing package ${ver}"
test/push_package.sh

echo ""
echo "Installing package ${ver}"

echo ""
echo "Compiling examples and smoke test for ${ver}"
test/compile.sh

echo ""
echo "Watiba ${ver} published."

