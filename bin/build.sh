#!/bin/bash

cd ~/git/watiba
rm -f dist/*
python3 setup.py sdist bdist_wheel

echo "__________________________"
echo "Dist is built"
echo "Push to Test PyPi?"
read yn
if [ "$yn" == "y" ]
then
  p=$(grep "password" .pypirc | head -1)
  echo "User: __token__"
  echo "$p"
  python3 -m twine upload --repository testpypi dist/*
fi