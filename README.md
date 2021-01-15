# Watiba
**Watiba documentation can be found in doc/watiba.md**

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
If you installed this as a Python package, e.g. pip, then the pre-compiler can be found
where the package was installed.  For example:
```
/home/{user}/.local/lib/python3.8/site-packages/watiba/watiba-c.py
```
This file can be copied to any directory in your PATH.  It is stand-alone and can be copied
anywhere you need.

## GITHUB
If you cloned this from github, you'll still need to install the package with pip, first, for the
watbia module.  Follow these steps to install Watiba locally.
```

# Must install Watiba package
pip3 install watiba

# Now run the pre-compiler
{watiba installation location}/bin/watiba-c.py your_file.wt > your_file.py
```

Optionally, you can copy watiba-c.py to a location in your PATH or add {watiba installation location}/bin/
to your exported PATH environment variable:
```
export PATH=${PATH}:{watiba installation location}/bin
```

# Pre-compiling
Once you've installed watiba-c.py into your path, you can execute it to pre-compile
your .wt (Watiba) code.  Output will be written to STDOUT, so you'll need to redirect
it to your final Python file.  Example follows:
```
watiba-c.py my_file.wt > my_file.py
chmod +x my_file.py
./my_file.py
```
To show the Watiba version of your pre-compiler, enter:
```
watiba-c.py version
```