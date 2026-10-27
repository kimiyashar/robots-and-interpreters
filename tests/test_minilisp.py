'''Unit tests for minilisp.py, checking every claim the lecture notes make.
Run from the project folder:   python3 -m unittest discover -s tests -v
'''
import contextlib, io, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from minilisp import tokenize, parse, evaluate, run, EOF, LispError
import minilisp

NOTES_CODE = '''
    (+  (+ 1 2)
        (* 3 4)
        (+ 5
           (* 6 7)))
'''

FIB = '''
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
                (set  x (+ x 1))
            )
        )
    )
'''

def captured(code):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        value = run(code)
    return value, buf.getvalue().splitlines()

class TestTokenize(unittest.TestCase):
    def test_notes_token_list(self):
        # notes, point 11
        expected = ['(', '+', '(', '+', 1, 2, ')', '(', '*', 3, 4, ')',
                    '(', '+', 5, '(', '*', 6, 7, ')', ')', ')', EOF]
        self.assertEqual(tokenize(NOTES_CODE), expected)

    def test_eof_is_chr0_and_last(self):
        self.assertEqual(EOF, chr(0))
        self.assertEqual(tokenize('(+ 1 2)')[-1], EOF)

    def test_whitespace_and_comments_removed(self):
        self.assertEqual(tokenize('  (+ 1   2) ? a comment ( ) 99\n'),
                         ['(', '+', 1, 2, ')', EOF])

    def test_multi_digit_numbers_are_ints(self):
        self.assertEqual(tokenize('123'), [123, EOF])
        self.assertIsInstance(tokenize('123')[0], int)

    def test_names(self):
        self.assertEqual(tokenize('(set total 5)'), ['(', 'set', 'total', 5, ')', EOF])

    def test_illegal_character(self):
        with self.assertRaises(LispError):
            tokenize('(+ 1 §)')

class TestParse(unittest.TestCase):
    def test_notes_parse_tree(self):
        # notes, point 15
        expected = ['+', ['+', 1, 2], ['*', 3, 4], ['+', 5, ['*', 6, 7]]]
        self.assertEqual(parse(tokenize(NOTES_CODE)), expected)

    def test_atoms(self):
        self.assertEqual(parse(tokenize('7')), 7)
        self.assertEqual(parse(tokenize('x')), 'x')

    def test_missing_paren(self):
        with self.assertRaises(LispError):
            parse(tokenize('(+ 1 (* 2 3)'))

    def test_deep_nesting(self):
        code = '(+ 1 ' * 50 + '1' + ')' * 50
        self.assertEqual(run(code), 51)

class TestEvaluate(unittest.TestCase):
    def test_notes_value_62(self):
        self.assertEqual(run(NOTES_CODE), 62)

    def test_simple_prefix(self):
        self.assertEqual(run('(+ 1 2 3)'), 6)  # notes, point 4

    def test_math(self):
        self.assertEqual(run('(- 20 3 4)'), 13)
        self.assertEqual(run('(* 2 3 4)'), 24)
        self.assertEqual(run('(/ 17 5)'), 3)
        self.assertEqual(run('(< 1 2 3)'), 1)
        self.assertEqual(run('(< 1 3 2)'), 0)

    def test_fib_output(self):
        value, lines = captured(FIB)
        expected = [f'[{i}, {f}]' for i, f in
                    enumerate([1, 1, 2, 3, 5, 8, 13, 21, 34, 55])]
        self.assertEqual(lines, expected)
        self.assertEqual(value, 10)

    def test_globals_dictionary(self):
        run('(block (set x 5) (set y 7))')
        self.assertEqual(minilisp.globalVars, {'x': 5, 'y': 7})

    def test_functions_map_stores_parms_and_body(self):
        # notes, point 19: name -> (parameter list, body parse tree)
        run('(function f (x y) (+ x y))')
        self.assertEqual(minilisp.functionsMap['f'], (['x', 'y'], ['+', 'x', 'y']))

    def test_new_local_dict_per_call(self):
        # a function cannot see globals, because it gets a brand new dict
        with self.assertRaises(LispError):
            run('(block (set g 10) (function f (x) (+ x g)) (f 1))')

    def test_locals_do_not_leak(self):
        run('(block (function f (x) (set inside x)) (f 3))')
        self.assertNotIn('inside', minilisp.globalVars)
        self.assertNotIn('x', minilisp.globalVars)

    def test_if_only_one_counts_as_true(self):
        self.assertEqual(run('(if 1 10 20)'), 10)
        self.assertEqual(run('(if 5 10 20)'), 20)

    def test_if_only_runs_one_branch(self):
        value, lines = captured('(if 1 (output 1) (output 2))')
        self.assertEqual(lines, ['[1]'])

    def test_while(self):
        value, lines = captured('(block (set i 0) (while (< i 3) (block (output i) (set i (+ i 1)))))')
        self.assertEqual(lines, ['[0]', '[1]', '[2]'])

    def test_errors(self):
        for bad in ['(frobnicate 1)', '(+ x 1)',
                    '(block (function f (x y) x) (f 1))']:
            with self.subTest(bad=bad), self.assertRaises(LispError):
                run(bad)

class TestEfficiency(unittest.TestCase):
    def test_tokenize_is_linear(self):
        # 200,000 characters would take many seconds with list.pop(0);
        # with an index it is instant.
        import time
        code = '(+ ' + '1 ' * 100000 + ')'
        start = time.perf_counter()
        tokens = tokenize(code)
        self.assertLess(time.perf_counter() - start, 2.0)
        self.assertEqual(len(tokens), 100004)
        self.assertEqual(run(code), 100000)

if __name__ == '__main__':
    unittest.main()
