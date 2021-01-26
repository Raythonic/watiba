#!/bin/bash
####################################################################################################
# This script does the following:
#  1. Update README with version and timestamp
#  2. Generate HTML version of README
#  3. Create pip freeze requirements file (list of dependencies)
#  4. Add and commit the changes above
#  5. Tag the version number (GIT)
#  6. Push new version to GITHUB current branch (prompted)
#  7. Merge branch with main (prompted)
#  8. Push new version to GITHUB branch main (prompted)
#  9. Build PIP package in dist/
#  10.  Push package to pypi.org and/or test.pypi.org (prompted)
#
# Author: Ray Walker  raythonic@gmail.com
####################################################################################################

# Make sure we're in the watiba virtual environment
declare -i chk_venv=$(which python3 | grep "watiba" | wc -l)

if [ $chk_venv -ne 1 ]
then
  echo "You forgot to source your venv"
  ls ~/.env
  exit 0
fi

# Make sure we're in a known CWD
cd ~/git/watiba

# Get our command line argument
parms="$1"

# Get current date
dat=$(date +"%Y\/%m\/%d")
log=logs/build_$(echo "$dat" | tr -d '/').log

# Find our git branch
branch=$(git branch | grep "\*" | awk '{print $2}')

if [ "$branch" == "main" ]
then
  echo "You're running under branch \"main\".  Go to the right branch, Doofus."
  exit 0
fi

# Create new version number based on last git tag
# This egrep finds that last version tag and filters out other kinds of tag names like "feature-blah"
declare -a current_ver=($(git tag | egrep "^v[0-9]+\.[0-9]+\.[0-9]+$" | tr -d 'v' | sort --version-sort | tail -1 | tr "." " "))
declare -i new_mod=${current_ver[2]}+1
declare new_ver=${current_ver[0]}"."${current_ver[1]}"."${new_mod}


# Validate what we're about to do
if [ "$parms" != "--silent" ]
then
  echo "-----------------------------------------------------------------------------------------"
  echo "Building in GIT branch \"${branch}\" version ${new_ver}."
  echo "(Don't worry, you'll get a chance to correct the version below.)"
  echo "Continue?"
  read yn
  if [ "$yn" != "y" ]
  then
    echo "Terminating."
    exit 0
  fi
fi

# Create a work space for version number change
if [ -d tmp ]
then
  rm -rf tmp
fi

mkdir tmp

# New source distribution
rm -rf dist
mkdir dist

resp=""
# Give user a chance to change the version number
if [ "$parms" != "--silent" ]
then
  echo "-----------------------------------------------------------------------------------------"
  echo "GIT tagging this release in branch \"${branch}\": v${new_ver}"
  echo "Hit ENTER to accept version, or enter new version number (no \"v\")"
  read resp

  while [ "$resp" != "" ]
  do
    declare -i chk_user_ver=$(echo "$resp" | egrep "^[0-9]+\.[0-9]+\.[0-9]+$" | wc -l)
    if [ $chk_user_ver -ne 1 ]
    then
      echo "Incorrect format!  Must be nn.nn.nn"
      echo "Re-enter new version number, or ENTER to keep version number ${new_ver}"
      read resp
    else
        new_ver=${resp}
        resp=""
    fi
  done
fi

# Publish our new version number
export WATIBA_VERSION=${new_ver}
echo "${new_ver}" > version.conf

# Get current date
dat=$(date +"%Y\/%m\/%d")

# Dump our dependencies
python3 -m pip freeze | grep -v "watiba" > requirements.txt

echo "-----------------------------------------------------------------------------------------"
echo "Compiling doc with new version ${new_ver}" | tee -a ${log}
chmod 777 README.md
rm README.md
sed "s/__version__/${new_ver}/g" < docs/watiba.md > README.md
sed -i "s/__current_date__/${dat}/g" README.md
markdown README.md > docs/README.html
chmod 0444 README.md

echo "-----------------------------------------------------------------------------------------"
echo "Building watiba-c script with new version ${new_ver}"  | tee -a ${log}
sed "s/__version__/${new_ver}/g" < watiba/watiba-c.py > bin/watiba-c

git add .
git commit -m "Build version ${new_ver}"
git tag -a v${new_ver} -m "Version ${new_ver}"

yn="y"
if [ "$parms" != "--silent" ]
then
  echo "-----------------------------------------------------------------------------------------"
  echo "Should I push ${new_ver} to github \"${branch}\"?"
  read yn
fi

if [ "$yn" == "y" ]
  then
    echo "Pushing changes to github ${branch}"  | tee -a ${log}
    git push origin ${branch} --tags
fi

yn="y"
if [ "$parms" != "--silent" ]
then
  echo "-----------------------------------------------------------------------------------------"
  echo "Should I merge \"${branch}\" into \"main\"?"
  read yn
fi

if [ "$yn" == "y" ]
then
  git checkout main
  chk=$(git branch | grep "\*" | awk '{print $2}')
  if [ "$chk" != "main" ]
  then
    echo "Error: cannot merge with main.  Checkout of main failed"  | tee -a ${log}
    exit 1
  fi

  echo "Merging ${branch} into main."
  git merge ${branch} -X theirs -m "Build ${new_ver}"

  yn="y"
  if [ "$parms" != "--silent" ]
  then
    echo "-----------------------------------------------------------------------------------------"
    echo "Should I push ${new_ver} to github \"main\"?"
    read yn
  fi
  if [ "$yn" == "y" ]
  then
    echo "Pushing changes to github main"  | tee -a ${log}
    git push origin main --tags
  fi
  git checkout ${branch}
fi

# Make sure we've returned to the branch we started with
# Make sure we've returned to the branch we started with
chk=$(git branch | grep "\*" | awk '{print $2}')
if [ "$chk" != "${branch}" ]
then
  echo "Error: cannot get back to branch \"${branch}\".  Failed to checkout \"${branch}\""  | tee -a ${log}
  exit 1
fi

echo "----------------------------------------------------------------------------------------------"
echo "Building PIP package"  | tee -a ${log}
python3 setup.py sdist

yn="y"
if [ "$parms" != "--silent" ]
then
  echo "----------------------------------------------------------------------------------------------"
  echo "Should I push the PIP package out?"
  read yn
fi

if [ "$yn" == "y" ]
then
  if [ "$parms" == "--silent" ]
  then
    echo "Pushing PIP package to both pypi and testpypi"  | tee -a ${log}
    bin/push_package.sh --both
  else
    bin/push_package.sh
  fi
fi
