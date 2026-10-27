# Robots & Interpreters

A study site for the two CMU 15-112 (Fall 2026) advanced topic lectures:

* [Advanced Topic: Robotics](https://www.cs.cmu.edu/~112/notes/advanced-topic-robotics.html)
* [Advanced Topic: Writing an Interpreter (for Lisp)](https://www.cs.cmu.edu/~112/notes/advanced-topic-lisp.html)

It assumes no prior knowledge and covers every point in both sets of notes.

**Live site: https://kimiyashar.github.io/robots-and-interpreters/**

An unofficial study guide, not affiliated with the course staff.

## What is on the site

| View | What it does |
| ---- | ------------ |
| Start | Overview, what the course expects, suggested study route |
| Robotics | Sense, Think, Act (with the MVC analogy), position vs force control, support polygon and ZMP, series elastic actuators, limitations timeline, lecture links |
| Interpreter | What Lisp is, prefix notation, interpreter vs compiler, Tokenize, Parse, Evaluate, dictionaries for variables and functions, the `pop(0)` shortcut and its fixes, the Fibonacci test |
| Playground | Type Lisp and run it. Shows the tokens, the parse tree, the output, and every evaluation step with the current scope and call stack. Includes the lecture examples and six "quirk" demos |
| Python code | `minilisp.py`, a complete interpreter, shown in six annotated sections |
| Quiz | 14 robotics and 19 interpreter questions with explanations |
| Cheat sheet | Both topics on one page |

## Files

```
index.html               the finished site, one self contained file (built, do not edit by hand)
template.html            page source: lessons, styles, playground, quizzes
engine.js                the browser interpreter used by the playground
minilisp.py              the Python interpreter shown on the Python code page
build.py                 combines template.html + engine.js + minilisp.py into index.html
tests/corpus.py          64 Lisp programs used for differential testing
tests/differential_test.py   lisp2.py vs minilisp.py vs engine.js
tests/test_minilisp.py   unit tests for every claim in the notes
tests/engine.test.js     browser engine tests (loop limits, recursion, trace)
tests/browser_check.py   headless browser test of the whole page, with screenshots
```

## How the interpreter matches lecture

`minilisp.py` and `engine.js` follow the lecture's `lisp2.py` design exactly (same commands, same `?` comments,
same `EOF = chr(0)`, same rule that `if` only treats exactly 1 as true and `while` only stops on exactly 0,
same new local dictionary per function call). The one deliberate change is the one the notes recommend:
they move an index through the input instead of calling `pop(0)`, so tokenizing and parsing are O(n)
instead of O(n squared). `engine.js` uses BigInt so arithmetic on huge numbers matches Python.

The differential test runs 64 programs (every lecture example, arithmetic edge cases, quirks, and 16 kinds of
errors) through all three implementations and requires identical tokens, parse trees, printed output and results.

## Running the tests

From this folder. The differential test compares against the lecture's own `lisp2.py`, which is not
included here because it is CMU's code. Download it first:

```
mkdir -p ref && curl -o ref/lisp2.py https://www.cs.cmu.edu/~112/notes/lisp2.py
python3 tests/differential_test.py            # 64/64 programs agree
python3 -m unittest discover -s tests -v      # 23 Python unit tests
node --test tests/engine.test.js              # 11 engine tests
python3 build.py && python3 tests/browser_check.py   # 80 page checks (needs: pip install playwright)
```

## Rebuilding the page

Edit `template.html`, `engine.js` or `minilisp.py`, then run `python3 build.py`.
