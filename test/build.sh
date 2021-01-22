#!/bin/bash

cd ~/git/watiba

# Find our git branch
branch=$(git branch | grep "\*" | awk '{print $2}')

echo "On git branch ${branch}.  Proceed?"
read yn
if [ "$yn" != "y" ]
then
  echo "Terminating."
  exit 0
fi

# Create a work space for version number change
if [ -d tmp ]
then
  rm -rf tmp
fi

mkdir tmp

# Build the dist package
declare -i version=$(git tag | tail -1 | tr -d 'v' | awk 'BEGIN {FS="."}{print $1}')
declare -i release=$(git tag | tail -1 | tr -d 'v' | awk 'BEGIN {FS="."}{print $2}')
declare -i mod=$(git tag | tail -1 | tr -d 'v' | awk 'BEGIN {FS="."}{print $3}')

mod=${mod}+1

new_ver=${version}"."${release}"."${mod}

echo "Git tagging this release: ${new_ver}"
echo "Hit enter to proceed or enter new version number"
read resp

if [ "$resp" != "" ]
then
  new_ver=${resp}
fi

export WATIBA_VERSION=${new_ver}



echo "Compiling md doc with new version ${new_ver}"
sed 's/__version__/${new_ver}/g' < README.template > README.md
markdown README.md > docs/README.html

echo "Building watiba-c script with new version ${new_ver}"
sed 's/__version__/${new_ver}/g' < watiba/watiba-c.py > bin/watiba-c

echo "Updating Poetry pyproject.toml file with new version ${new_ver}.  Overwriting pyporject.toml!!"
echo "Press enter to continue"
read yn
sed "s/__version__/${new_ver}/g" < pyproject.template > pyproject.toml

git add .
git commit -m "Build version ${new_ver}"
git tag -a v${new_ver} -m "Version ${new_ver}"

if [ "$branch" != "main" ]
then
  echo ""
  echo "Merge ${branch} into main?"
  read yn

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
    git tag -a v${new_ver} -m "Version ${new_ver}"
    git push origin
    git checkout ${branch}
  fi

  chk=$(git branch | head -1 | awk '{print $2}')
  if [ "chk" != "${branch}"]
  then
    echo "Error: cannot get back to branch ${branch}.  Failed to checkout ${branch}"
    exit 1
  fi
fi

echo "Running poetry build"
poetry build
