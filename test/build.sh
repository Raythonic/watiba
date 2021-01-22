#!/bin/bash

cd ~/git/watiba

parms="$1"

# Find our git branch
branch=$(git branch | grep "\*" | awk '{print $2}')

if [ "$parms" != "--silent" ]
then
  echo "On git branch ${branch}.  Proceed?"
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

rm -rf dist
mkdir dist

# Build the dist package
declare -a current_ver=($(git describe --abbrev=0 | tail -1 | tr -d 'v' | tr '.' ' '))
declare -i new_mod=${current_ver[2]}+1
declare new_ver=${current_ver[0]}"."${current_ver[1]}"."${new_mod}

echo "Git tagging this release: ${new_ver}"

resp=""
if [ "$parms" != "--silent" ]
then
  echo "Hit enter to proceed or enter new version number"
  read resp
fi

if [ "$resp" != "" ]
then
  new_ver=${resp}
fi

# Publish our new version number
export WATIBA_VERSION=${new_ver}
echo "${new_ver}" > version.conf

# Get current date
dat=$(date +"%Y\/%m\/%d")

echo "Compiling md doc with new version ${new_ver}"
sed "s/__version__/${new_ver}/g" < docs/watiba.md > README.md
sed -i "s/__current_date__/${dat}/g" README.md
markdown README.md > docs/README.html

echo "Building watiba-c script with new version ${new_ver}"
sed "s/__version__/${new_ver}/g" < watiba/watiba-c.py > bin/watiba-c

git add .
git commit -m "Build version ${new_ver}"
git tag -a v${new_ver} -m "Version ${new_ver}"

yn="y"
if [ "$parms" != "--silent" ]
then
  echo "Push ${new_ver} to github ${branch}?"
  read yn
fi

if [ "$yn" == "y" ]
  then
    echo "Pushing changes to github ${branch}"
    git push origin
fi

if [ "$branch" != "main" ]
then

  if [ "$parms" != "--silent" ]
  then
    echo ""
    echo "Merge ${branch} into main?"
    read yn
  else
    echo "Merging ${branch} into main."
    yn="y"
  fi

  if [ "$yn" == "y" ]
  then
    git checkout main
    chk=$(git branch | grep "\*" | awk '{print $2}')
    if [ "$chk" != "main" ]
    then
      echo "Error: cannot merge with main.  Checkout of main failed"
      exit 1
    fi
    git add .
    git merge ${branch}

    yn="y"
    if [ "$parms" != "--silent" ]
    then
      echo "Push ${new_ver} to github ${branch}?"
      read yn
    fi
    if [ "$yn" == "y" ]
    then
      echo "Pushing changes to github ${branch}"
      git push origin
    fi
    git checkout ${branch}
  fi

  chk=$(git branch | grep "\*" | awk '{print $2}')
  if [ "$chk" != "${branch}" ]
  then
    echo "Error: cannot get back to branch ${branch}.  Failed to checkout ${branch}"
    exit 1
  fi
fi

echo "Running build"
python3 setup.py sdist
