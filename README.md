# Watiba
**Watiba documentation can be found in doc/watiba.html** or on the Github Wiki for project watiba.

Watiba, pronounced wah-TEE-bah, is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.  It is similar to other languages' syntactical enhancements where
XML or HTML is integrated into a language such as JavaScript.  That is the concept applied here but integrating
BASH shell commands with Python.

As you browse this document, you'll find Watiba is rich with features for shell command integration with Python.

Features:
- Shell command integration with Python code
- Current directory context maintained across commands throughout your Python code
- Async/promise support for integrated shell commands
- Remote shell command execution
- Remote shell command chaining and piping

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands. 
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory 
after the execution of any shell command so that all subsequent shell commands keep context.  For example:

```
#!/usr/bin/python3

if __name__ == "__main__":
    `cd /tmp`
    for l in `ls -lrt`.stdout:
        print(l)
```



# Installation
## PIP
If you installed this as a Python package, e.g. pip, then the pre-compiler can be 
found in your user's home dir at _~/.local/bin/watiba-c_ should that location exists on your system.

If your system doesn't have _~/.local/bin_, refer to the "Pre-compiling" section below.

## GITHUB
If you cloned this from github, you'll still need to install the package with pip, first, for the
watbia module.  Follow these steps to install Watiba locally.
```
# Watiba package required
pip install watiba
```

The pre-compiler can be found in your user's home dir at _~/.local/bin/watiba-c_
If your system doesn't have _~/.local/bin_, refer to the "Pre-compiling" section below.

# Pre-compiling
Test that the pre-compiler functions in your environment:
```
watiba-c version
```
For example:
```buildoutcfg
rwalk@walkubu:~$ watiba-c version
Watiba 0.3.26
Python 3.8
```
_Note_: The Watiba PIP installation attempts to locate your python interpreter and writes it as the first line
in _~/.local/bin/watiba-c_.  If it is, however, incorrect, you'll need to edit the first line of
_~/.local/bin/watiba-c_ to properly load Python.

Example of first line of _~/.local/bin/watiba-c_watiba-c_:
```buildoutcfg
#!/usr/bin/python3
```

If your system does not have a _~/.local/bin_, then you'll have to copy watiba/watiba-c-bin.py from the package installation location to a
location that's in your PATH.

Example assuming the location of the package, and assuming ~/bin is in your PATH:
```buildoutcfg
cp ~/.local/lib/python3.8/site-packages/watiba/watiba-c-bin.py ~/bin/watiba-c
```

To pre-compile a .wt file:
```
watiba-c my_file.wt > my_file.py
chmod +x my_file.py
./my_file.py
```

Where _my_file.wt_ is your Watiba code.

