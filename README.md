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
found in your user's home dir at _.local/bin/watiba-c_

## GITHUB
If you cloned this from github, you'll still need to install the package with pip, first, for the
watbia module.  Follow these steps to install Watiba locally.
```
# Watiba package required
pip install watiba
```

The pre-compiler can be found in your user's home dir at _.local/bin/watiba-c_

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
_Note_: watiba-c assumes your python interpreter is in _/usr/bin/python3_.  If it is not, edit the first line of
 _.local/bin/watiba-c_ to properly load Python.

To pre-compile a .wt file:
```
watiba-c my_file.wt > my_file.py
chmod +x my_file.py
./my_file.py
```

Where _my_file.wt_ is your Watiba code.

