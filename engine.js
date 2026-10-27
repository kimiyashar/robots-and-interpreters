/* MiniLisp engine: a JavaScript mirror of minilisp.py (and lecture's lisp2.py).
   Numbers are BigInt so arithmetic matches Python exactly.
   evaluate() records a trace of events so the page can step through it. */
const MiniLisp = (() => {
  'use strict';
  const EOF = '\u0000';
  const COMMENT_CHAR = '?';
  const PUNCT = new Set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'); // Python string.punctuation

  class LispError extends Error {
    constructor(message, stage) { super(message); this.stage = stage || 'evaluate'; }
  }

  const isSpace = c => /\s/u.test(c);
  const isDigit = c => c >= '0' && c <= '9';
  const isAlpha = c => /\p{L}/u.test(c);
  const isInt = x => typeof x === 'bigint';

  /* ===== STEP 1: TOKENIZE ===== */
  function tokenize(code) {
    code += EOF;
    const tokens = [];
    let i = 0;
    while (code[i] !== EOF) {
      const c = code[i];
      if (isSpace(c)) {
        i += 1;
      } else if (c === COMMENT_CHAR) {
        while (code[i] !== '\n' && code[i] !== EOF) i += 1;
      } else if (isDigit(c)) {
        const start = i;
        while (isDigit(code[i])) i += 1;
        tokens.push(BigInt(code.slice(start, i)));
      } else if (isAlpha(c)) {
        const start = i;
        while (isAlpha(code[i])) i += 1;
        tokens.push(code.slice(start, i));
      } else if (PUNCT.has(c)) {
        tokens.push(c);
        i += 1;
      } else {
        throw new LispError(`Illegal character: ${pyRepr(c)}. Only letters, digits, spaces and punctuation are allowed.`, 'tokenize');
      }
    }
    tokens.push(EOF);
    return tokens;
  }

  /* ===== STEP 2: PARSE ===== */
  function parse(tokens) {
    return parseExpression(tokens, 0)[0];
  }
  function parseExpression(tokens, i) {
    const token = tokens[i];
    if (token === EOF || token === undefined) {
      throw new LispError("The code ended too early. Is a ')' missing?", 'parse');
    } else if (token === '(') {
      const cmd = tokens[i + 1];
      if (cmd === EOF || cmd === undefined) {
        throw new LispError("The code ended too early. Is a ')' missing?", 'parse');
      }
      const tree = [cmd];
      i += 2;
      while (tokens[i] !== ')') {
        if (tokens[i] === EOF || tokens[i] === undefined) {
          throw new LispError("The code ended too early. Is a ')' missing?", 'parse');
        }
        const [child, next] = parseExpression(tokens, i);
        tree.push(child);
        i = next;
      }
      return [tree, i + 1];
    }
    return [token, i + 1];
  }

  /* ===== Python style repr, so output matches what Python prints ===== */
  function pyRepr(x) {
    if (isInt(x)) return x.toString();
    if (Array.isArray(x)) return '[' + x.map(pyRepr).join(', ') + ']';
    if (typeof x === 'string') {
      if (x === EOF) return "'\\x00'";
      if (x.includes("'") && !x.includes('"')) return '"' + x.replace(/\\/g, '\\\\') + '"';
      return "'" + x.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
    }
    return String(x);
  }
  // Lisp style source text for a parse tree node, e.g. (+ 1 (* 2 3))
  function toLisp(x) {
    if (Array.isArray(x)) return '(' + x.map(toLisp).join(' ') + ')';
    if (isInt(x)) return x.toString();
    return x === EOF ? 'EOF' : String(x);
  }

  /* ===== math helpers (same behavior as Python, including errors) ===== */
  function needOne(L, cmd) {
    if (L.length === 0) throw new LispError(`(${cmd}) needs at least one argument. Python would raise IndexError here.`);
  }
  function floorDiv(a, b) {
    if (b === 0n) throw new LispError('Division by zero. Python would raise ZeroDivisionError here.');
    let q = a / b;
    if (a % b !== 0n && ((a < 0n) !== (b < 0n))) q -= 1n;
    return q;
  }
  const helpers = {
    '+': L => L.reduce((s, v) => s + v, 0n),
    '*': L => { needOne(L, '*'); return L.slice(1).reduce((r, v) => r * v, L[0]); },
    '/': L => { needOne(L, '/'); return L.slice(1).reduce((r, v) => floorDiv(r, v), L[0]); },
    '-': L => { needOne(L, '-'); return L.slice(1).reduce((r, v) => r - v, L[0]); },
    '<': L => { for (let i = 1; i < L.length; i++) if (L[i - 1] >= L[i]) return 0n; return 1n; },
  };

  // Variables live in a Map. Python dict keys here are names (str) or, in
  // odd programs like (set 5 3), ints. Keep those from colliding.
  const keyOf = k => {
    if (isInt(k)) return 'int:' + k.toString();
    if (typeof k === 'string') return k;
    throw new LispError(`${toLisp(k)} cannot be used as a variable name. Python would raise TypeError (unhashable list).`);
  };
  const nameOf = key => key.startsWith('int:') ? key.slice(4) : key;

  /* ===== STEP 3: EVALUATE (with a recorded trace) ===== */
  function run(code, opts = {}) {
    const maxSteps = opts.maxSteps ?? 300000;
    const maxDepth = opts.maxDepth ?? 2500;
    const maxEvents = opts.maxEvents ?? 30000;
    const result = { tokens: null, tree: null, outputs: [], value: null, error: null,
                     events: [], truncated: false, steps: 0, globals: [], functions: [] };
    try { result.tokens = tokenize(code); }
    catch (e) { result.error = asError(e, 'tokenize'); return result; }
    try { result.tree = parse(result.tokens.slice()); }
    catch (e) { result.error = asError(e, 'parse'); return result; }

    const functionsMap = new Map();
    const globalFrame = { label: 'global', vars: new Map() };
    const frames = [globalFrame];
    let scopeSnap = snapshot(globalFrame);
    let stackSnap = ['global'];
    let steps = 0;

    function snapshot(frame) {
      return { label: frame.label, vars: [...frame.vars].map(([k, v]) => [nameOf(k), v.toString()]) };
    }
    function record(ev) {
      if (result.events.length >= maxEvents) { result.truncated = true; return; }
      ev.s = scopeSnap; ev.k = stackSnap;
      result.events.push(ev);
    }

    function evaluate(node, frame, path, depth) {
      steps += 1;
      if (steps > maxSteps) {
        throw new LispError(`Stopped after ${maxSteps.toLocaleString()} steps. This is probably an infinite loop: a while only stops when its test becomes exactly 0.`);
      }
      if (depth > maxDepth) {
        throw new LispError('Too much recursion (is a function calling itself forever?). Python would raise RecursionError here.');
      }
      record({ t: 'in', p: path, d: depth });
      const value = evaluateInner(node, frame, path, depth);
      record({ t: 'out', p: path, d: depth, v: value.toString() });
      return value;
    }

    function arg(args, i, cmd) {
      if (i >= args.length) {
        throw new LispError(`(${cmd} ...) is missing an argument. Python would raise IndexError here.`);
      }
      return args[i];
    }

    function evaluateInner(node, frame, path, depth) {
      if (isInt(node)) return node;
      if (typeof node === 'string') {
        const key = keyOf(node);
        if (!frame.vars.has(key)) {
          const hint = frame === globalFrame ? '' :
            ` Inside a function you can only see that function's parameters and the variables it sets, never globals.`;
          throw new LispError(`Undefined variable: ${node === EOF ? 'EOF' : node}.${hint}`);
        }
        return frame.vars.get(key);
      }
      if (!Array.isArray(node)) throw new LispError(`Illegal parse tree: ${pyRepr(node)}`);
      const cmd = node[0];
      const args = node.slice(1);
      const kid = i => path + '.' + (i + 1); // path of args[i]

      if (cmd === 'set') {
        const name = arg(args, 0, cmd);
        const key = keyOf(name);
        const value = evaluate(arg(args, 1, cmd), frame, kid(1), depth + 1);
        frame.vars.set(key, value);
        scopeSnap = snapshot(frame);
        record({ t: 'msg', p: path, d: depth, text: `${toLisp(name)} is now ${value} (in the ${frame.label === 'global' ? 'global' : frame.label} scope)` });
        return value;
      }
      if (cmd === 'if') {
        const cond = evaluate(arg(args, 0, cmd), frame, kid(0), depth + 1);
        if (cond === 1n) {
          record({ t: 'msg', p: path, d: depth, text: `Test gave 1, so only the THEN branch runs.` });
          return evaluate(arg(args, 1, cmd), frame, kid(1), depth + 1);
        }
        record({ t: 'msg', p: path, d: depth, text: `Test gave ${cond}, which is not 1, so only the ELSE branch runs.` });
        return evaluate(arg(args, 2, cmd), frame, kid(2), depth + 1);
      }
      if (cmd === 'while') {
        let res = 0n;
        while (true) {
          const cond = evaluate(arg(args, 0, cmd), frame, kid(0), depth + 1);
          if (cond === 0n) {
            record({ t: 'msg', p: path, d: depth, text: `Test gave 0, so the loop ends and returns ${res}.` });
            return res;
          }
          record({ t: 'msg', p: path, d: depth, text: `Test gave ${cond} (not 0), so the body runs again.` });
          res = evaluate(arg(args, 1, cmd), frame, kid(1), depth + 1);
        }
      }
      if (cmd === 'function') {
        const name = arg(args, 0, cmd), parms = arg(args, 1, cmd), body = arg(args, 2, cmd);
        functionsMap.set(name, { parms, body, bodyPath: kid(2) });
        record({ t: 'msg', p: path, d: depth, text: `Stored function ${toLisp(name)} with parameters ${toLisp(parms)}. Its body does not run yet.` });
        return 0n;
      }

      const ev = args.map((a, i) => evaluate(a, frame, kid(i), depth + 1));
      if (Object.prototype.hasOwnProperty.call(helpers, cmd)) return helpers[cmd](ev);
      if (cmd === 'block') {
        if (ev.length === 0) throw new LispError('(block) needs at least one expression. Python would raise IndexError here.');
        return ev[ev.length - 1];
      }
      if (cmd === 'output') {
        const line = pyRepr(ev);
        result.outputs.push(line);
        record({ t: 'msg', p: path, d: depth, text: `Printed ${line}`, out: true });
        return 0n;
      }
      if (functionsMap.has(cmd)) {
        const fn = functionsMap.get(cmd);
        let parms = fn.parms;
        if (typeof parms === 'string') parms = [...parms];   // Python len()/zip() on a str works char by char
        if (!Array.isArray(parms)) throw new LispError(`The parameter list of ${toLisp(cmd)} is not a list. Python would raise TypeError here.`);
        if (ev.length !== parms.length) {
          throw new LispError(`Wrong number of arguments to ${toLisp(cmd)}: it takes ${parms.length} but got ${ev.length}.`);
        }
        const local = { label: '', vars: new Map() };
        parms.forEach((p, i) => local.vars.set(keyOf(p), ev[i]));
        local.label = `${toLisp(cmd)}(${parms.map((p, i) => `${toLisp(p)}=${ev[i]}`).join(', ')})`;
        frames.push(local);
        const savedScope = scopeSnap, savedStack = stackSnap;
        scopeSnap = snapshot(local);
        stackSnap = stackSnap.concat(local.label);
        record({ t: 'msg', p: path, d: depth, text: `Calling ${local.label}: a brand new local dictionary is created for it.`, call: fn.bodyPath });
        let value;
        try {
          value = evaluate(fn.body, local, fn.bodyPath, depth + 1);
        } finally {
          frames.pop();
          scopeSnap = savedScope; stackSnap = savedStack;
        }
        record({ t: 'msg', p: path, d: depth, text: `${local.label} returned ${value}. Its local dictionary is thrown away.` });
        return value;
      }
      throw new LispError(`Unknown command: ${toLisp(cmd)}`);
    }

    try {
      result.value = evaluate(result.tree, globalFrame, 'r', 0);
    } catch (e) {
      result.error = asError(e, 'evaluate');
    }
    result.steps = steps;
    result.globals = snapshot(globalFrame).vars;
    result.functions = [...functionsMap].map(([n, f]) => [toLisp(n), toLisp(f.parms)]);
    return result;
  }

  function asError(e, stage) {
    if (e instanceof LispError) return { message: e.message, stage: e.stage === 'evaluate' ? stage : e.stage };
    if (e instanceof RangeError) {
      return { message: 'Too much recursion for the browser to handle. Python would raise RecursionError here.', stage };
    }
    return { message: String(e && e.message || e), stage };
  }

  return { EOF, tokenize, parse, run, pyRepr, toLisp, LispError, isInt };
})();
if (typeof module !== 'undefined') module.exports = MiniLisp;
