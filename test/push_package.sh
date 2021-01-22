#!/bin/bash
cd ~/git/watiba

echo "Enter:"
echo "   t - test pypi"
echo "   p - pypi (public)"
echo "   B - both"
read resp

if [ "$resp" == "t" ] || [ "$resp" == "B" ]
then
  echo "Pushing watiba to TEST pypi"
  python3 -m twine upload --repository testpypi dist/*
fi

if [ "$resp" == "p" ] || [ "$resp" == "B" ]
then
  echo "Pushing watiba to PUBLIC pypi"
  python3 -m twine upload --repository pypi dist/*
fi

