#!/bin/python3
versions = ["Watiba 0.1.2", "Python 3.8"]
import sys
import re

"""
Watiba pre-complier.  Watiba commands are BASH embedded commands between backtick characters (i.e. `), like traditional Bash captures.

Examples:
  example1.wt
    for line in `ls -lrt`.stdout:
        print(line)
    
    w = `cd /tmp && tar -zxvf blah.zip`
    if w.exit_code != 0:
        for l in w.stderr:
            print(l, file=stderr)

Author:
Ray Walker
raythonic@gmail.com

"""

watiba_ref = "_watiba_"


# Singleton object.
class Compiler:
    def __init__(self, first_stmt):
        self.output = [first_stmt,
                       "import watiba",
                       "{} = watiba.Watiba()".format(watiba_ref)
                       ]
        self.resolver_count = 1
        self.async_call = []
        self.indentation_count = -1
        self.spawn_args = "{}"

    # Handle spawn code blocks
    def spawn_handler(self, parms):

        # Build the async call that will be located just after the resolver block
        quote_style = "'" if "'" not in parms["match"].group(2) else '"'
        cmd = parms["match"].group(2) if parms["match"].group(2)[0] == "$" else "{}{}{}".format(quote_style, parms["match"].group(2), quote_style)
        resolver_name = "{}__watiba_resolver_{}__".format(parms["prefix"], self.resolver_count)
        self.resolver_count += 1

        self_prefix = "" if parms["prefix"] == "" else parms["prefix"].replace(".", ", ")

        # Include promise return if there's an assignment on the stmt
        promise_assign = parms["match"].group(1) if parms["match"].group(1) else ""

        # Queue up asyc call which is executed (spit out) at the end of the w_async block
        self.async_call.append("{}_watiba_.spawn({}{}, {}, {})".format(promise_assign, self_prefix, cmd, resolver_name, self.spawn_args))
        self.spawn_args = "{}"

        # Track the indentation level at the time we hit the w_async statement
        #   This way we know when to spit out the async call at the end of the block
        self.indentation_count = len(parms["statement"]) - len(parms["statement"].lstrip())

        # Convert spawn `cmd`: statement to proper Python function definition
        self.output.append(["def {}(promise):".format(resolver_name)])

    # Flush out any queue async calls that are located after the resolver block
    def flush(self):
        # Spit out async calls if they're queued up
        while len(self.async_call) > 0:
            print(self.async_call.pop())

    # Generator for spawn in class
    def spawn_handler_self(self, parms):
        self.output.append(self.spawn_handler({"match":parms["match"],
                                   "statement": parms["statement"],
                                   "prefix": "self."}))

    # Generator for spawn args statement.  (S is not used)
    def spawn_args_handler(self, parms):
        self.spawn_args = parms["match"].group(1)


    def backticks_hander(self, parms):
        s = str(parms["statement"])

        # Flag for Watiba CWD tracking
        context = True

        # Run through the statement and replace backticked shell commands with Watiba function calls
        m = parms["match"]
        while m:
            # This flag control Watiba's CWD tracking
            context = False if m.group(1) == "-" else True
            cmd = m.group(2)

            # Make sure the string to be replaced as a dash or not
            repl_str = "{}`{}`".format("-" if not context else "", cmd)

            # Replace the backticked commands with a Watiba function call
            if cmd[0] == "$":
                cmd = cmd[1:]
            else:
                quote_style = "'" if cmd.find("'") < 0 else '"'
                cmd = "{}{}{}".format(quote_style, cmd, quote_style)
            s = s.replace(repl_str, "{}.bash({}, {})".format(watiba_ref, cmd, context), 1)

            # Test for more backticked commands
            m = re.search(parms["pattern"], s)

        self.output.append(s)

    # Compile the passed statement
    def compile(self, stmt):

        # Copy the statement to a local variable
        s = str(stmt)

        # Spit out async call if it's queued up
        if len(self.async_call) > 0 and len(s) - len(s.lstrip()) <= self.indentation_count:
            self.output.append(self.async_call.pop())
            self.async_call = []
            self.indentation_count = len(s) - len(s.lstrip())

        expressions = {"^spawn args\((\S.*)\)$": self.spawn_args_handler,
                       "^(\S.*)?self.spawn `(\S.*)`:$": self.spawn_handler_self,
                       "^(\S.*)?spawn `(\S.*)`:$": self.spawn_handler,
                       ".*?([\-])?`(\S.*?)`.*?": self.backticks_handler
                       }


        # Check the statement for a Watiba expresion
        for ex in expressions:
            m = re.search(ex, s.strip())

            # We have a Watiba expression. Generate the code.
            if m:
                return expressions[ex]({"match":m, "statement": s, "pattern":ex})


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
                c.compile(statement.rstrip())
                for o in c.output:
                    print(o)
                c.output = []

    # Flush out any queued async statement calls
    c.flush()

