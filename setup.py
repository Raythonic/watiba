import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Watiba_Raythonic", # Replace with your own username
    version="0.0.2",
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