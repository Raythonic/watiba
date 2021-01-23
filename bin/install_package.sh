#!/bin/bash
pip3 uninstall watiba
echo "Enter t to install from testpypi, p for pypi (public)"
read resp

if [ "$resp" == "t" ]
then
  echo "Installing watiba from TEST"
  python3 -m pip install --index-url https://test.pypi.org/simple watiba
else
  echo "installing watiba from PROD"
  python3 -m pip install watiba
fi
