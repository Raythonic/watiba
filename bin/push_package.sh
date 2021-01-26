#!/bin/bash
cd ~/git/watiba

parms=${1}
resp=""

case "${parms}" in
  '--both')
      resp="B"
      ;;
  '--test')
      resp="t"
      ;;
  '--prod')
      resp="p"
      ;;
esac

if [ "$resp" == "" ]
then
  echo "Enter:"
  echo "   t - test pypi"
  echo "   p - pypi (public)"
  echo "   B - both"
  read resp
fi

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

