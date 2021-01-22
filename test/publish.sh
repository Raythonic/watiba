#!/bin/bash
cd /home/rwalk/git/watiba
test/build.sh
ver=$(cat version.conf)
echo "Build of ${ver} successful"

branch=$(git branch | grep "\*" | awk '{print $2}')
echo ""
echo "I will now push ${ver} to github branch ${branch}"
echo "Is this correct?"
read yn
if [ "$yn" != "y" ]
then
  echo "Terminating."
  exit 0
fi

echo ""
echo "Committing to git: Latest build for version ${ver}"
git add .
git commit -m "Latest build for version ${ver}"
git push origin
echo "Successfully pushed ${ver} to github branch ${branch}"

echo ""
echo "I will now push the Python package"
test/push_package.sh

echo ""
echo "I will now uninstall the current py package and install the new one"
test/install_package.sh

echo ""
echo "I will now compile the examples test Watiba code"
test/compile.sh

echo ""
echo "Watiba published."

