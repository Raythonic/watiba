#!/usr/bin/python3.8
import sys
import re

versions = ["Watiba 0.0.1",
            "Python 3.8"]

"""
Watiba complier.  Watiba are BASH embedded commands between escape characters (i.e. `), like traditional Bash.

Examples:
  example1.wt
    for line in `ls -lrt`:
        print(line)

Author:
Ray Walker
raythonic@gmail.com

"""

watiba_ref = "_watiba_"

class Compiler:
    def __init__(self, first_stmt):
        self.output = [first_stmt,
                    "import watiba",
                    "{} = watiba.Watiba()".format(watiba_ref)
                    ]

    def compile(self, stmt):

        # Make a copy of the statement string
        s = str(stmt)

        # Regex expression for catching backticked shell commands
        exp = ".*?(\-)?`(\S.*?)`.*?"

        # Take a copy of initial generated code
        output = self.output.copy()

        # Remove initial statements so they're not generated for every shell commands
        self.output = []

        # Flag for Watiba CWD tracking
        context = True

        # Run through the statement and replace backticked shell commands with Watiba function calls
        m = re.search(exp, s)
        while m:
            # This flag control Watiba's CWD tracking
            context = False if m.group(1) == "-" else True

            # Make sure the string to be replaced as a dash or not
            repl_str = "{}`{}`".format("-" if not context else "", m.group(2))

            # Replace the backticked commands with a Watiba function call
            s = s.replace(repl_str , "{}.bash('{}', {})".format(watiba_ref, m.group(2), context), 1)

            # Test for more backticked commands
            m = re.search(exp, s)

        output.append(s)
        return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR. No input file.")
        sys.exit(0)

    if sys.argv[1] == "version":
        for v in versions:
            print(v)
        sys.exit(0)

    in_file = sys.argv[1]
    if not re.match(r".*\.wt$", in_file):
        print("ERROR: Input file must be type .wt.  Found {}".format(in_file))
        sys.exit(1)

    out_file = in_file.replace('.wt', '.py', 1)
    c = None

    with open(in_file, 'r') as f:
        for statement in f:
            if not c:
                c = Compiler(statement.rstrip())
            else:
                for o in c.compile(statement.rstrip()):
                    print(o)
