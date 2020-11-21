#!/bin/bash
cd /home/rwalk/git/watiba
echo "Run build first?"
read yn
if [ "$yn" == "y" ]
then
  echo "Building Watiba"
  bin/build.sh
fi

echo "Testing Watiba"
bin/watiba-c.py test/examples.wt > tmp/watiba_test.py
chmod +x tmp/watiba_test.py