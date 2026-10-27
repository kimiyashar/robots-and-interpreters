'''
minilisp.py

A tiny Lisp interpreter built the same way as the one written live in
CMU 15-112 lecture: Tokenize, then Parse, then Evaluate.

It understands the same small language as the lecture's lisp2.py:
    numbers:     0, 7, 123            (whole numbers only, no negatives)
    variables:   x, total, fib        (letters only)
    comments:    ? anything after a question mark, to the end of the line
    commands:    (+ a b ...)  (- a b ...)  (* a b ...)  (/ a b ...)
                 (< a b ...)            -> 1 if strictly increasing, else 0
                 (set NAME VALUE)       -> store a variable
                 (if TEST THEN ELSE)    -> THEN runs only when TEST is exactly 1
                 (while TEST BODY)      -> repeats until TEST is 0
                 (block E1 E2 ... En)   -> runs each, returns the last
                 (output E1 ... En)     -> prints the values as a list
                 (function NAME (P1 ... Pk) BODY)

One deliberate difference from lecture: the tokenizer and parser walk
through their input with an index i instead of calling list.pop(0).
pop(0) has to shift every remaining item left, so it costs O(n) each
time, which makes the whole tokenizer O(n**2). Moving an index costs
O(1), so tokenizing and parsing are both O(n). The lecture notes list
this exact fix (along with reversing the list or using a deque).

Run this file to see the lecture's fib example, or run the tests in
tests/test_minilisp.py.
'''

import string

EOF = chr(0)          # special end of file marker; chr(0) never appears in real code
COMMENT_CHAR = '?'    # same comment character as lecture's lisp2.py

class LispError(Exception):
    '''Raised for any mistake in the Lisp program we are running.'''

# =====================================================================
# STEP 1: TOKENIZE
# Input:  the code, one big multiline string
# Output: a flat 1D list of tokens, ending with EOF
# =====================================================================

def tokenize(code):
    code += EOF
    tokens = [ ]
    i = 0
    while code[i] != EOF:
        c = code[i]
        if c.isspace():
            # whitespace only separates tokens, so we skip it
            i += 1
        elif c == COMMENT_CHAR:
            # skip everything up to (not including) the end of the line
            while code[i] not in ['\n', EOF]:
                i += 1
        elif c.isdigit():
            # a number: keep reading digits, then convert to an int
            start = i
            while code[i].isdigit():
                i += 1
            tokens.append(int(code[start:i]))
        elif c.isalpha():
            # a name: keep reading letters
            start = i
            while code[i].isalpha():
                i += 1
            tokens.append(code[start:i])
        elif c in string.punctuation:
            # punctuation like ( ) + * < is always a 1 character token
            tokens.append(c)
            i += 1
        else:
            raise LispError(f'Illegal character: {c!r}')
    tokens.append(EOF)
    return tokens

# =====================================================================
# STEP 2: PARSE
# Input:  the 1D list of tokens
# Output: a parse tree, built from nested lists
#         (+ 1 (* 2 3))  becomes  ['+', 1, ['*', 2, 3]]
# =====================================================================

def parse(tokens):
    parseTree, nextIndex = parseExpression(tokens, 0)
    return parseTree

def parseExpression(tokens, i):
    # Parses ONE expression that starts at tokens[i].
    # Returns (the parse tree for it, the index just past it).
    token = tokens[i]
    if token == EOF:
        raise LispError("The code ended too early. Is a ')' missing?")
    elif token == '(':
        # ( CMD ARG ARG ... ARG )
        cmd = tokens[i + 1]
        if cmd == EOF:
            raise LispError("The code ended too early. Is a ')' missing?")
        parseTree = [ cmd ]
        i += 2
        while tokens[i] != ')':
            # each argument can itself be a whole expression, so we
            # recurse: this is why parsing handles any depth of nesting
            child, i = parseExpression(tokens, i)
            parseTree.append(child)
        return parseTree, i + 1   # i + 1 skips over the ')'
    else:
        # an int or a name stands for itself
        return token, i + 1

# =====================================================================
# STEP 3: EVALUATE
# Input:  a parse tree
# Output: the value it computes (and any printing it does along the way)
# =====================================================================

globalVars = dict()     # variable name -> value, for the top level
functionsMap = dict()   # function name -> (parameter list, body parse tree)

def evaluate(parseTree, localVars=None):
    if localVars == None:
        localVars = globalVars
    if isinstance(parseTree, int):
        # a number evaluates to itself
        return parseTree
    elif isinstance(parseTree, str):
        # a name evaluates to that variable's current value
        varName = parseTree
        if varName not in localVars:
            raise LispError(f'Undefined variable: {varName}')
        return localVars[varName]
    elif isinstance(parseTree, list):
        cmd = parseTree[0]
        args = parseTree[1:]

        # Special forms: these decide for themselves which arguments
        # to evaluate, so we must handle them BEFORE evaluating args.
        if cmd == 'set':
            # (set NAME VALUE): NAME is not evaluated, VALUE is
            varName = args[0]
            varValue = evaluate(args[1], localVars)
            localVars[varName] = varValue
            return varValue
        elif cmd == 'if':
            # (if TEST THEN ELSE): only one branch ever runs
            condition = evaluate(args[0], localVars)
            if condition == 1:
                return evaluate(args[1], localVars)
            else:
                return evaluate(args[2], localVars)
        elif cmd == 'while':
            # (while TEST BODY): returns the body's last value, or 0
            result = 0
            while True:
                condition = evaluate(args[0], localVars)
                if condition == 0:
                    return result
                result = evaluate(args[1], localVars)
        elif cmd == 'function':
            # (function NAME PARMS BODY): store it, do not run it yet
            fnName = args[0]
            parms = args[1]
            body = args[2]
            functionsMap[fnName] = (parms, body)
            return 0

        # Everything else is a normal call: evaluate every argument first
        evaluatedArgs = [evaluate(arg, localVars) for arg in args]
        if cmd == '+': return sum(evaluatedArgs)
        elif cmd == '*': return multiply(evaluatedArgs)
        elif cmd == '/': return divide(evaluatedArgs)
        elif cmd == '-': return subtract(evaluatedArgs)
        elif cmd == '<': return lessThan(evaluatedArgs)
        elif cmd == 'block': return evaluatedArgs[-1]
        elif cmd == 'output': print(evaluatedArgs); return 0
        elif cmd in functionsMap:
            # a user defined function call
            parms, body = functionsMap[cmd]
            if len(evaluatedArgs) != len(parms):
                raise LispError(f'Wrong number of arguments to {cmd}')
            # brand new dictionary = brand new local scope
            localVars = dict()
            for parm, arg in zip(parms, evaluatedArgs):
                localVars[parm] = arg
            return evaluate(body, localVars)
        else:
            raise LispError(f'Unknown command: {cmd}')
    else:
        raise LispError(f'Illegal parse tree: {parseTree}')

# Helpers for the math commands. Each takes the list of evaluated args.

def multiply(L):
    result = L[0]
    for v in L[1:]: result *= v
    return result

def divide(L):
    result = L[0]
    for v in L[1:]: result //= v    # integer (floor) division
    return result

def subtract(L):
    result = L[0]
    for v in L[1:]: result -= v
    return result

def lessThan(L):
    # (< a b c) is 1 only if a < b < c
    for i in range(1, len(L)):
        if L[i-1] >= L[i]:
            return 0
    return 1

# =====================================================================
# PUTTING IT TOGETHER
# =====================================================================

def run(code):
    '''Tokenize, parse, and evaluate code with fresh globals.'''
    globalVars.clear()
    functionsMap.clear()
    return evaluate(parse(tokenize(code)))

if __name__ == '__main__':
    code = '''
        (block
            (function fib (n)
                (if (< n 2)
                    1
                    (+ (fib (- n 1))
                       (fib (- n 2))
                    )
                )
            )
            (set x 0)
            (while (< x 10)
                (block
                    (output x (fib x))
                    (set x (+ x 1))
                )
            )
        )
    '''
    print('tokens:   ', tokenize(code))
    print('parseTree:', parse(tokenize(code)))
    print('-----')
    print('result:   ', run(code))
