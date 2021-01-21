import setuptools
import os
from shutil import copyfile

# Populate the package's long version with README
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get our new version number
with open("version.conf", "r") as fh:
    new_version = fh.read().strip()

# Prepare to create a watiba-c pre-compiler executable on the user's system
home = os.path.expanduser("~")

# If this user has a .local/bin in their home directory, build the executable there
if os.path.exists(f'{home}/.local/bin'):
    copyfile("watiba/watiba-c-bin.py", f"{home}/.local/bin/watiba-c")
    os.chmod(f"{home}/.local/bin/watiba-c", 0o755)

setuptools.setup(
    name="watiba", # Replace with your own username
    version=new_version,
    author="Ray Walker",
    author_email="raythonic@gmail.com",
    license="MIT",
    description="Python syntactical sugar for embedded shell commands",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Raythonic/watiba",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    data_files=["version.conf"]
)