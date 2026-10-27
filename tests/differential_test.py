'''Differential test: lecture lisp2.py vs minilisp.py vs engine.js.

For every program in corpus.py we compare:
    tokens (Python repr), parse tree (Python repr),
    printed output lines, and the final result (or that an error happened).

Run from the project folder:   python3 tests/differential_test.py
'''
import contextlib, io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import minilisp
from corpus import CORPUS

def loadLecture():
    path = os.path.join(ROOT, 'ref', 'lisp2.py')
    if not os.path.exists(path):
        sys.exit('ref/lisp2.py is missing. Download the lecture file first:\n'
                 '  mkdir -p ref && curl -o ref/lisp2.py https://www.cs.cmu.edu/~112/notes/lisp2.py')
    src = open(path).read()
    src = src[:src.index("\ncode = '''")]   # drop the demo code at the bottom
    ns = {}
    exec(src, ns)
    return ns

def runPython(code, tokenize, parse, evaluate, resetState):
    out = {'tokens': None, 'tree': None, 'outputs': [], 'result': None}
    try:
        out['tokens'] = repr(tokenize(code))
    except Exception:
        out['result'] = 'ERROR'; return out
    try:
        out['tree'] = repr(parse(tokenize(code)))
    except Exception:
        out['result'] = 'ERROR'; return out
    resetState()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            value = evaluate(parse(tokenize(code)))
        out['result'] = repr(value)
    except BaseException as e:   # RecursionError, KeyError, IndexError, ...
        if isinstance(e, KeyboardInterrupt): raise
        out['result'] = 'ERROR'
    out['outputs'] = [line for line in buf.getvalue().splitlines()]
    return out

def runJS():
    script = r'''
      const L = require(process.argv[1]);
      const progs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
      const res = {};
      for (const [name, code] of Object.entries(progs)) {
        const r = L.run(code);
        const o = { tokens: r.tokens ? L.pyRepr(r.tokens) : null,
                    tree: r.tree !== null ? L.pyRepr(r.tree) : null,
                    outputs: r.outputs,
                    result: r.error ? 'ERROR' : L.pyRepr(r.value),
                    stage: r.error ? r.error.stage : null };
        if (r.error && r.error.stage === 'tokenize') o.tokens = null;
        if (r.error && r.error.stage !== 'evaluate') o.tree = null;
        res[name] = o;
      }
      process.stdout.write(JSON.stringify(res));
    '''
    p = subprocess.run(['node', '-e', script, os.path.join(ROOT, 'engine.js')],
                       input=json.dumps(CORPUS), capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

def main():
    lec = loadLecture()
    def resetLecture():
        lec['globalVars'].clear(); lec['functionsMap'].clear()
    def resetMini():
        minilisp.globalVars.clear(); minilisp.functionsMap.clear()
    js = runJS()
    failures = 0
    for name, code in CORPUS.items():
        a = runPython(code, lec['tokenize'], lec['parse'], lec['evaluate'], resetLecture)
        b = runPython(code, minilisp.tokenize, minilisp.parse, minilisp.evaluate, resetMini)
        c = {k: js[name][k] for k in ('tokens', 'tree', 'outputs', 'result')}
        # The lecture code reports some errors later than ours (for example it
        # happily parses an empty program, then fails while evaluating). Only
        # compare a stage when every implementation got past it.
        def comparable(key):
            return all(x[key] is not None for x in (a, b, c))
        problems = []
        for key in ('tokens', 'tree'):
            if comparable(key) and not (a[key] == b[key] == c[key]):
                problems.append(f'{key} differ:\n  lisp2: {a[key]}\n  mini:  {b[key]}\n  js:    {c[key]}')
        if not (a['result'] == b['result'] == c['result']):
            problems.append(f'result differ: lisp2={a["result"]} mini={b["result"]} js={c["result"]}')
        if not (a['outputs'] == b['outputs'] == c['outputs']):
            problems.append(f'outputs differ:\n  lisp2: {a["outputs"]}\n  mini:  {b["outputs"]}\n  js:    {c["outputs"]}')
        status = 'ok ' if not problems else 'FAIL'
        print(f'{status} {name:40s} result={a["result"]}  outputs={len(a["outputs"])}')
        for p in problems:
            print('     ' + p)
        failures += bool(problems)
    print(f'\n{len(CORPUS) - failures}/{len(CORPUS)} programs agree across lisp2.py, minilisp.py and engine.js')
    sys.exit(1 if failures else 0)

if __name__ == '__main__':
    main()
