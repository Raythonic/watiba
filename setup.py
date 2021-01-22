import setuptools

# Populate the package's long version with README
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get our new version number
with open("version.conf", "r") as fh:
    new_version = fh.read().strip()

setuptools.setup(
    name="watiba",
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
    scripts=["bin/watiba-c"],
    data_files=["version.conf"]
)