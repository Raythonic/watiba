import setuptools
import os
import sys

if os.path.exists("doc"):
    with open("doc/watiba.md", "r") as fh:
        long_description = fh.read()
else:
    with open("README.md", "r") as fh:
        long_description = fh.read()
        home = os.path.expanduser("~")
        if os.path.exists(f'{home}/.local/bin'):
            py_loc = f'#!{sys.executable}\n'
            dest_file = f"{home}/.local/bin/watiba-c"
            with open("watiba/version.py") as f:
                ver = f.read()
                ver_line = f'versions = ["Watiba {ver}", "Python 3.8"]\n'
                with open(dest_file, 'w') as wf:
                    wf.write(py_loc)
                    wf.write(ver_line)
                    with open("watiba/watiba-c.py", 'r') as rf:
                        wf.write(rf.read())

                os.chmod(dest_file, 0o0766)
        else:
            print(f"WARNING: {home}/.local/bin not found on this system.  "
                  f"Please copy watiba/watiba-c-bin.py to a location within your PATH")


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