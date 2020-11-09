#!/usr/bin/python3.8
import sys
import re

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
        s = stmt
        exp = ".*?(\-)?`(\S.*?)`.*?"
        output = self.output.copy()
        self.output = []
        context = True

        m = re.search(exp, s)
        while m:
            context = False if m.group(1) == "-" else True
            dash = "-" if not context else ""
            repl_str = "{}`{}`".format(dash, m.group(2))
            print("groups: {}".format(m.groups()), file=sys.stderr)
            s = s.replace(repl_str , "{}.bash('{}', {})".format(watiba_ref, m.group(2), context), 1)
            m = re.search(exp, s)

        output.append(s)
        return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR. No input file.")
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
