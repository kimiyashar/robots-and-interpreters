// Browser engine tests (features the Python versions do not need).
// Run from the project folder:   node --test tests/
const test = require('node:test');
const assert = require('node:assert');
const L = require('../engine.js');

const FIB = `(block
  (function fib (n) (if (< n 2) 1 (+ (fib (- n 1)) (fib (- n 2)))))
  (set x 0)
  (while (< x 10) (block (output x (fib x)) (set x (+ x 1)))))`;

test('infinite while loop is stopped with a helpful message', () => {
  const r = L.run('(while 1 (+ 1 1))', { maxSteps: 5000 });
  assert.ok(r.error);
  assert.match(r.error.message, /infinite loop/);
});

test('(while 5 ...) also loops forever, because only 0 stops it', () => {
  const r = L.run('(while 5 0)', { maxSteps: 2000 });
  assert.match(r.error.message, /infinite loop/);
});

test('runaway recursion is stopped', () => {
  const r = L.run('(block (function f (n) (f n)) (f 1))');
  assert.ok(r.error);
  assert.match(r.error.message, /recursion/i);
});

test('outputs printed before an error are kept', () => {
  const r = L.run('(block (output 1) (oops 2))');
  assert.deepStrictEqual(r.outputs, ['[1]']);
  assert.match(r.error.message, /Unknown command: oops/);
});

test('trace is balanced: every in has a matching out', () => {
  const r = L.run(FIB);
  assert.ok(!r.error);
  const ins = r.events.filter(e => e.t === 'in').length;
  const outs = r.events.filter(e => e.t === 'out').length;
  assert.strictEqual(ins, outs);
  assert.strictEqual(ins, r.steps);
  assert.strictEqual(r.events.at(-1).p, 'r');
  assert.strictEqual(r.events.at(-1).v, '10');
});

test('paths in the trace point at real nodes in the parse tree', () => {
  const r = L.run(FIB);
  const nodeAt = path => path.split('.').slice(1).reduce((n, i) => n[Number(i)], r.tree);
  for (const e of r.events.filter(e => e.t === 'in')) {
    assert.notStrictEqual(nodeAt(e.p), undefined, e.p);
  }
});

test('function call shows a new local scope, then the global scope returns', () => {
  const r = L.run('(block (set g 1) (function f (x) (* x 2)) (f 21))');
  const call = r.events.find(e => e.t === 'msg' && e.call);
  assert.ok(call.text.includes('f(x=21)'));
  const inside = r.events.find(e => e.t === 'in' && e.p === call.call);
  assert.strictEqual(inside.s.label, 'f(x=21)');
  assert.deepStrictEqual(inside.s.vars, [['x', '21']]);
  assert.deepStrictEqual(inside.k, ['global', 'f(x=21)']);
  assert.deepStrictEqual(r.events.at(-1).k, ['global']);
  assert.deepStrictEqual(r.globals, [['g', '1']]);
  assert.deepStrictEqual(r.functions, [['f', '(x)']]);
});

test('trace is capped but the run still finishes correctly', () => {
  const r = L.run(FIB, { maxEvents: 100 });
  assert.strictEqual(r.events.length, 100);
  assert.ok(r.truncated);
  assert.strictEqual(r.outputs.length, 10);
  assert.strictEqual(r.value, 10n);
});

test('error stage is reported', () => {
  assert.strictEqual(L.run('(+ 1 §)').error.stage, 'tokenize');
  assert.strictEqual(L.run('(+ 1').error.stage, 'parse');
  assert.strictEqual(L.run('(+ x 1)').error.stage, 'evaluate');
});

test('function scope error explains that globals are invisible', () => {
  const r = L.run('(block (set g 10) (function f (x) (+ x g)) (f 1))');
  assert.match(r.error.message, /never globals/);
});

test('pyRepr matches Python repr for tricky tokens', () => {
  assert.strictEqual(L.pyRepr(["'", '\\', L.EOF, 5n, ['a']]), `["'", '\\\\', '\\x00', 5, ['a']]`);
});
