#!/bin/bash

cd ~/git/watiba
rm -rf dist
mkdir dist

# Increment the version number
ver=$(bin/__version__.py)

# Create a work space for version number change
if [ -d tmp ]
then
  rm -rf tmp
fi

mkdir tmp

# Put version number in Watiba compiler code and build the dist package
echo "#!/bin/python3" > bin/watiba-c.py
echo "versions = [\"Watiba $ver\", \"Python 3.8\"]" >> bin/watiba-c.py
cat watiba/watiba-c.py >> bin/watiba-c.py
cp watiba/watiba.py tmp/.

# Build the dist package
python3 setup.py sdist

# Push package to distribution site
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