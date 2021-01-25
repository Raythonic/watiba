#!/bin/bash
cd ~/git/watiba
bin/build.sh
ver=$WATIBA_VERSION
echo "Build of ${ver} successful"

echo ""
echo "Pushing package ${ver}"
bin/push_package.sh

echo ""
echo "Installing package ${ver}"
bin/install_package.sh

echo ""
echo "Compiling examples and smoke test for ${ver}"
bin/compile.sh

echo ""
echo "Watiba ${ver} published."

