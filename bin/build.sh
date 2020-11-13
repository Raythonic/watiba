#!/bin/bash

cd ~/git/watiba
rm -f dist/*

# Increment the version number
bin/__version__.py
ver=$(cat .version)

# Create a work space for version number change
if [ -d tmp ]
then
  rm -rf tmp
fi

mkdir tmp

# Put version number in Watiba compiler code and build the dist package
cp src/watiba-c.py tmp/.
echo "#!/bin/python3" > tmp/temp.py
echo "versions = [\"Watiba $ver\", \"Python 3.8\"]" >> tmp/temp.py
cat src/watiba-c.py >> tmp/temp.py
cp tmp/temp.py src/watiba-c.py

# Build the dist package
python3 setup.py sdist bdist_wheel

# Restore original code
cp tmp/watiba-c.py src/.

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