import setuptools
import os
import sys

# Populate the package's long version with README
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get our new version number
with open("watiba/version.py", "r") as fh:
    new_version = fh.read().strip()

# Test will only exist on the building server
if not os.path.exists("test"):
    # If we land here, we're installing in the user's environment

    # Prepare to create a watiba-c pre-compiler executable on the user's system
    home = os.path.expanduser("~")

    # If this user has a .local/bin in their home directory, build the executable there
    if os.path.exists(f'{home}/.local/bin'):
        # Find out where their python interpreter is located
        py_loc = f'#!{sys.executable}\n'

        # Set the executable destination
        dest_file = f"{home}/.local/bin/watiba-c"

        # Create the executable in ~/.local/bin/watiba-c
        with open(dest_file, 'w') as wf:
            # Python interpreter from user's environment
            wf.write(py_loc)

            # Create new executable for user's environment
            with open("watiba/watiba-c-bin.py", 'r') as rf:
                # Used to skip first line in executable
                write = False
                # Skip first line
                for line in rf.readlines():
                    if write:
                        wf.write(line)
                    write = True
        # Make it executable
        os.chmod(dest_file, 0o0766)


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
)