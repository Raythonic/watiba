#!/usr/bin/env python3
versions = ["__version__"]

'''
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

'''
import re
import sys

watiba_ref = "_watiba_"


# Singleton object.
class Compiler:
    def __init__(self):
        self.first_time = True
        self.current_statement = ""
        self.output = ["import watiba",
                       f"{watiba_ref} = watiba.Watiba()"
                       ]
        self.resolver_count = 1
        self.spawn_call = []
        self.last_stmt = ""
        self.stmt_count = 1

        # Regex expressions for Watiba commands (order matters otherwise backticks would win over spawn)
        self.expressions = {
            # p = spawn `cmd`@host: block
            "^(\S.*)?spawn \s*`(\S.*)`@(\S.*) \s*?(\S.*)?:.*": self.spawn_generator_with_host,

            # p = spawn `cmd`@host: block
            "^(\S.*)?spawn \s*`(\S.*)`@(\S.*)\s*?(\S.*)?:.*": self.spawn_generator_with_host,

            # p = spawn `cmd`@host args: block
            "^(\S.*)?spawn \s*`(\S.*)`@(\S.*) \s*?(\S.*)?:.*": self.spawn_generator_with_host,

            # p = spawn `cmd` args: block
            "^(\S.*)?spawn \s*`(\S.*)`\s*?(\S.*)?:.*": self.spawn_generator,

            # spawn-ctl {args}
            "^spawn-ctl \s*(\S.*)": self.spawn_ctl_args,

            # watbia-ctl {args}
            "^watiba-ctl \s*(\S.*)": self.watiba_ctl_args,

            # chain {host:cmd...
            "^(\S.*)?chain \s*`(\S.*)` \s*(\S.*)": self.chain_generator,

            # `cmd`@host
            ".*?([\-])?`(\S.*?)`@(\S.*) .*?": self.backticks_generator_with_host,

            # `cmd`
            ".*?([\-])?`(\S.*?)`.*?": self.backticks_generator
        }

    # Flush output and any queue spawn calls that are located after the resolver block
    def flush(self, final=False):
        # Statements to ignore when looking for block terminations
        nothingness = ["#"]

        if final and len(self.spawn_call) > 0:
            if re.search("^return ", self.last_stmt.strip()):
                # Spit out spawn calls if they're queued up
                while len(self.spawn_call) > 0:
                    print(self.spawn_call.pop())
            else:
                print("ERROR in flush: Resolver block not properly terminated with return.", file=sys.stderr)
                print(f"    Block at line {self.stmt_count} incorrectly terminated with:", file=sys.stderr)
                print(f"      {self.last_stmt}", file=sys.stderr)
                sys.exit(1)

        # Print our generated output
        if not self.first_time:
            while len(self.output) > 0:
                print(self.output.pop(0))

            if len(self.current_statement.strip()) > 0:
                self.last_stmt = self.current_statement if self.current_statement.lstrip()[
                                                               0] not in nothingness else self.last_stmt

    # Generate chain command
    def chain_generator(self, parms):
        assignment = parms["match"].group(1) if parms["match"].group(1) else ""
        quote_type = "'" if "'" not in parms["match"].group(2) else '"'
        cmd = f'{quote_type}{parms["match"].group(2)}{quote_type}' if parms["match"].group(2)[0] != "$" else parms[
            "match"].group(2).replace("$", "")
        args = parms["match"].group(3)

        self.output.append(f'{parms["indentation"]}{assignment}{watiba_ref}.chain({cmd}, {args})')

    # Set spawn controller args
    def spawn_ctl_args(self, parms):
        self.output.append(f'{parms["indentation"]}{watiba_ref}.spawn_ctlr.set_parms({parms["match"].group(1)})')

    # Set watiba control args
    def watiba_ctl_args(self, parms):
        self.output.append(f'{parms["indentation"]}{watiba_ref}.set_parms({parms["match"].group(1)})')

    # Handle spawn code blocks (with host specified)
    def spawn_generator_with_host(self, parms):
        self.spawn_generator(parms, host=parms["match"].group(3))

    # Handle spawn code blocks
    def spawn_generator(self, parms, host=None):
        hostname = host if host else "localhost"
        assign_idx = 1
        cmd_idx = 2
        args_idx = 3 if not host else 4

        # Build the spawn call that will be located just after the resolver block
        quote_style = "'" if "'" not in parms["match"].group(cmd_idx) else '"'

        # extract the command and if it's a variable, remove the $ and no quotes, otherwise in quotes
        cmd = parms["match"].group(cmd_idx)[1:] if parms["match"].group(cmd_idx)[
                                                       0] == "$" else f'{quote_style}{parms["match"].group(cmd_idx)}{quote_style}'
        # Build the next resolver method name
        resolver_name = f"__watiba_resolver_{self.resolver_count}__"
        self.resolver_count += 1

        # Include promise return if there's an assignment on the stmt
        promise_assign = parms["match"].group(assign_idx) if parms["match"].group(assign_idx) else ""

        # Add in args if there's any
        resolver_args = parms["match"].group(args_idx) if parms["match"].group(args_idx) else "{}"

        h = f'"{hostname}"' if hostname[0] != "$" else hostname
        h = h.replace("$", "") if h and h[0] == "$" else h

        # Queue up async call which is executed (spit out) at the end of the w_spawn block
        self.spawn_call.append(
            f'{parms["indentation"]}{promise_assign}{watiba_ref}.spawn({cmd}, {resolver_name}, {resolver_args}, {"locals()"}, {h})')

        # Convert spawn `cmd`: statement to proper Python function definition
        self.output.append(f'{parms["indentation"]}def {resolver_name}(promise, args):')

    # Generator for `cmd` expressions
    def backticks_generator_with_host(self, parms):
        host = parms["match"].group(3)
        if host[0] == "$":
            host = host.replace("$", "")
        else:
            host = f'"{host}"'
        self.backticks_generator(parms, host)

    # Generator for `cmd` expressions
    def backticks_generator(self, parms, host=None):
        s = str(parms["statement"])

        # Run through the statement and replace ALL the backticked shell commands with Watiba function calls
        m = parms["match"]
        while m:
            # This flag control Watiba's CWD tracking
            context = False if m.group(1) == "-" else True
            cmd = m.group(2)

            # Make sure the string to be replaced includes the dash if needed
            repl_str = f'{"-" if not context else ""}`{cmd}`'

            # Replace the backticked commands with a Watiba function call
            if cmd[0] == "$":
                cmd = cmd[1:]
            else:
                quote_style = "'" if cmd.find("'") < 0 else '"'
                cmd = f"{quote_style}{cmd}{quote_style}"
            if not host:
                s = s.replace(repl_str, f"{watiba_ref}.bash({cmd}, {context})", 1)
            else:
                s = s.replace(repl_str, f"{watiba_ref}.ssh({cmd}, {host}, {context})", 1)
            # Test for more backticked commands
            m = re.search(parms["pattern"], s)

        self.output.append(s)

    # Compile the passed statement
    def compile(self, stmt):
        # If this is the first statement to compile, keep it to generate the #! version header stuff...
        if self.first_time:
            self.output.insert(0, stmt)
            self.first_time = False
            return

        # Track our current statement
        self.current_statement = stmt

        # Copy the statement to a local variable
        s = str(stmt)
        self.stmt_count += 1

        # Spit out spawn call if it's queued up (on block breaks)

        # Indention level of current statement
        stmt_level = len(s) - len(s.lstrip()) if len(s.strip()) > 0 and s.lstrip()[0] != "#" else -1

        # Indention level of last spawn expression
        spawn_level = len(self.spawn_call[-1]) - len(self.spawn_call[-1].lstrip()) if len(self.spawn_call) > 0 else -1

        # If we're on an indention change and there's valid levels to compare,
        #   check if we're done with the resolver block
        resolver_level_completed = stmt_level == spawn_level if stmt_level != -1 else False

        # If done with the resolver block, did it terminate with a resolve value?
        if resolver_level_completed:
            if re.search("^return ", self.last_stmt.strip()):
                print(self.spawn_call.pop())
            else:
                print("ERROR: Resolver block not properly terminated with return.", file=sys.stderr)
                print(f"    Block at line {self.stmt_count} incorrectly terminated with:", file=sys.stderr)
                print(f"      {self.last_stmt}", file=sys.stderr)
                sys.exit(1)

        # Check the statement for a Watiba expresion
        for ex in self.expressions:
            m = re.search(ex, s.strip())

            # We have a Watiba expression. Generate the code.
            if m:
                return self.expressions[ex](
                    {"match": m,
                     "statement": s,
                     "pattern": ex,
                     "indentation": stmt[0:len(stmt) - len(stmt.lstrip())]
                     })

        self.output.append(stmt)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR. No input file.")
        sys.exit(0)

    # the versions array is generated at build time (see this module in bin/)
    if sys.argv[1] == "version":
        for v in versions:
            print(v)
        sys.exit(0)

    in_file = sys.argv[1]
    if not re.match(r".*\.wt$", in_file):
        print(f"ERROR: Input file must be type .wt.  Found {in_file}")
        sys.exit(1)

    # Instantiate a compiler
    c = Compiler()

    # Read through input file and compile each statement
    with open(in_file, 'r') as f:
        for statement in f:
            # Compile this line of input
            c.compile(statement.rstrip())

            # Spit out the output of the compiler
            c.flush()

    # Flush out any queued spawn statement calls
    c.flush(final=True)
