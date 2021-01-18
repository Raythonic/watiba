import setuptools
import os
import sys

if os.path.exists("doc"):
    with open("doc/watiba.md", "r") as fh:
        long_description = fh.read()
else:
    # If we land here, we're installing in the user's environment

    # Only load the README not the full doc, which is on the pypi.org site
    with open("README.md", "r") as fh:
        long_description = fh.read()

        # Prepare to create a watiba-c pre-compiler executable on the user's system
        home = os.path.expanduser("~")

        # If this user has a .local/bin in their home directory, build the executable there
        if os.path.exists(f'{home}/.local/bin'):
            # Find out where their python interpreter is located
            py_loc = f'#!{sys.executable}\n'

            # Set the executable destination
            dest_file = f"{home}/.local/bin/watiba-c"

            # Get the current version number
            with open("watiba/version.py") as f:
                ver = f.read()

                # Build a line of code for the executable
                ver_line = f'versions = ["Watiba {ver}", "Python 3.8"]\n'

                # Create the executable in ~/.local/bin/watiba-c
                with open(dest_file, 'w') as wf:
                    wf.write(py_loc)
                    wf.write(ver_line)
                    with open("watiba/watiba-c.py", 'r') as rf:
                        wf.write(rf.read())
                # Make it executable
                os.chmod(dest_file, 0o0766)


with open("watiba/version.py", "r") as fh:
    new_version = fh.read().strip()

setuptools.setup(
    name="watiba", # Replace with your own username
    version=new_version,
    author="Ray Walker",
    author_email="raythonic@gmail.com",
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