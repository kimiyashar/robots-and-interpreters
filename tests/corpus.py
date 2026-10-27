'''Lisp programs used by the differential tests. Each one is run through
the lecture's lisp2.py, minilisp.py, and the browser engine (engine.js),
and all three must agree.'''

CORPUS = {
    # ===== lecture examples (lisp2.py) =====
    'lecture2_arith': '''
        (+ (* 3 4)  ? 12
           (/ 10 2) ? 5
        ) ? 17
    ''',
    'lecture2_block_set': '''
        (block
            (set x (+ 1 4))
            (* x 5) ? 25
            (output (* x 100))
        )
    ''',
    'lecture2_while': '''
        (block
            (set x 5)
            (while (< x 10)
                (block
                    (set x (+ 1 x))
                    (output x)
                )
            )
        )
    ''',
    'lecture2_function': '''
        (block
            (function f (x y)
                (+ x y)
            )
            (f 2 3)
        )
    ''',
    'lecture_fib': '''
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
    ''',
    # ===== lecture examples (lisp1.py, comments switched from ! to ?) =====
    'lecture1_nested': '''
        (+  (+ 10 2) ? 12
            (+  9 2) ? 11
            8
        ) ? 31
    ''',
    'lecture1_mixed': '''
        (+  (* 10 2) ?
            (/ 10 2)  ?  5
            (- 10 2)  ?  8
        ) ? 33
    ''',
    'lecture1_fact': '''
        (block
            (function fact (n)
                (if (< n 2)
                    1
                    (* n (fact (- n 1)))
                )
            )
            (set x 0)
            (while (< x 10)
                (block
                    (output x (fact x))
                    (set  x (+ x 1))
                )
            )
        )
    ''',
    # ===== the notes' worked example =====
    'notes_62': '''
        (+  (+ 1 2)
            (* 3 4)
            (+ 5
               (* 6 7)))
    ''',
    # ===== arithmetic edge cases =====
    'sum_empty': '(+)',
    'sum_one': '(+ 7)',
    'sub_many': '(- 20 3 4 5)',
    'sub_negative': '(- 2 5)',
    'sub_one': '(- 5)',
    'floor_div': '(/ 17 5)',
    'floor_div_negative': '(/ (- 0 7) 2)',
    'floor_div_neg_exact': '(/ (- 0 8) 2)',
    'div_chain': '(/ 100 2 5)',
    'big_numbers': '(* 123456789 987654321 1000000007 31415926535)',
    'big_fact': '''
        (block
            (function fact (n) (if (< n 2) 1 (* n (fact (- n 1)))))
            (fact 30))
    ''',
    'less_chain_true': '(< 1 2 3 4)',
    'less_chain_false': '(< 1 3 2)',
    'less_equal_is_false': '(< 2 2)',
    'less_empty': '(<)',
    'less_one': '(< 9)',
    'nested_deep': '(+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1))))))))',
    # ===== quirks worth knowing =====
    'if_five_is_false': '(if 5 100 200)',
    'if_one_is_true': '(if 1 100 200)',
    'if_zero': '(if 0 100 200)',
    'while_never_runs': '(while 0 (output 1))',
    'while_returns_last': '''
        (block (set i 0) (while (< i 3) (block (set i (+ i 1)) (* i 10))))
    ''',
    'set_returns_value': '(set x 42)',
    'block_returns_last': '(block 1 2 3)',
    'function_returns_zero': '(function f (x) x)',
    'output_returns_zero': '(output 1 2 3)',
    'output_empty': '(output)',
    'extra_close_paren_ignored': '(+ 1 2)) junk',
    'just_a_number': '5',
    'multi_digit_then_name': '(block (set ab 4) (+ 12 ab))',
    'comment_at_end_no_newline': '(+ 1 2) ? done',
    'comment_only_lines': '''
        ? this whole line is a comment
        (+ 4 5) ? and so is this tail
        ? (+ 100 100) this never runs
    ''',
    'unicode_letters': '(block (set café 3) (* café 2))',
    'set_int_name': '(set 5 3)',
    'function_string_parms': '(block (function f x (+ x 1)) (f 2))',
    'function_two_calls_share_nothing': '''
        (block
            (function g (a) (block (set b (* a 2)) b))
            (output (g 3) (g 4)))
    ''',
    'recursive_sum': '''
        (block
            (function total (n) (if (< n 1) 0 (+ n (total (- n 1)))))
            (total 50))
    ''',
    'function_overrides_nothing_builtin': '''
        (block (function block (x) 99) (block 1 2))
    ''',
    'outputs_then_error': '''
        (block (output 1) (output 2) (frobnicate 3))
    ''',
    # ===== errors (all three must raise) =====
    'err_unknown_cmd': '(frobnicate 1 2)',
    'err_undefined_var': '(+ x 1)',
    'err_function_cannot_see_globals': '''
        (block
            (set g 10)
            (function f (x) (+ x g))
            (f 1))
    ''',
    'err_wrong_arg_count': '(block (function f (x y) (+ x y)) (f 1))',
    'err_missing_paren': '(+ 1 (* 2 3)',
    'err_empty_program': '',
    'err_only_comment': '? nothing here',
    'err_illegal_char': '(+ 1 §)',
    'err_div_zero': '(/ 5 0)',
    'err_mul_empty': '(*)',
    'err_block_empty': '(block)',
    'err_if_missing_else': '(if 0 1)',
    'err_set_list_name': '(set (+ 1 2) 5)',
    'err_lone_paren': '(',
    'err_close_first': ')',
    'err_var_at_top': 'x',
}
