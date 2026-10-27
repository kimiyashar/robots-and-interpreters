'''Headless browser check of the built page (needs Python playwright).
Clicks through every view and the playground, checks for script errors
and sideways scrolling, and saves screenshots to tests/shots/.
Run from the project folder:   python3 tests/browser_check.py
'''
import os, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, 'tests', 'shots')
os.makedirs(SHOTS, exist_ok=True)

test_file = os.path.join(ROOT, 'index.html')   # already a complete HTML document
URL = 'file://' + test_file

VIEWS = ['start', 'robotics', 'interpreter', 'playground', 'code', 'quiz', 'cheatsheet']
failures = []

def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: failures.append(msg)

def no_overflow(page, label):
    w = page.evaluate('[document.documentElement.scrollWidth, window.innerWidth]')
    check(w[0] <= w[1], f'{label}: no sideways scroll ({w[0]} <= {w[1]})')

with sync_playwright() as p:
    browser = p.chromium.launch()
    for scheme, width, height, tag in [('light', 1280, 900, 'desk-light'), ('dark', 390, 844, 'phone-dark')]:
        ctx = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=scheme)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_' not in m.text else None)
        print(f'== {tag}')
        for v in VIEWS:
            page.goto(URL + '#' + v)
            page.wait_for_timeout(250)
            visible = page.evaluate(f"!document.getElementById('view-{v}').hidden")
            check(visible, f'view {v} shows')
            no_overflow(page, v)
            page.screenshot(path=os.path.join(SHOTS, f'{tag}-{v}.png'), full_page=(v in ('start', 'cheatsheet')))

        # ===== playground interactions =====
        page.goto(URL + '#playground'); page.wait_for_timeout(200)
        check(page.locator('#tree-box .tn').count() > 5, 'notes example tree rendered')
        check('62' in page.inner_text('#results'), 'notes example result is 62')
        for _ in range(6): page.click('[data-act="next"]')
        check('step 7 of' in page.inner_text('#step-count'), 'next button advances')
        check(page.locator('.tn.current').count() == 1, 'exactly one current node highlighted')
        page.select_option('#example', 'fib'); page.wait_for_timeout(300)
        out = page.inner_text('#results')
        check('[9, 55]' in out and '[0, 1]' in out, 'fib prints [0, 1] through [9, 55]')
        page.click('[data-act="call"]')
        check('fib(n=' in page.inner_text('#now'), 'Next call jumps to a fib call')
        check(page.locator('#stack span').count() == 2, 'call stack shows global plus fib')
        page.click('[data-act="print"]')
        check('Printed [0, 1]' in page.inner_text('#now'), 'Next print jumps to first print')
        page.click('[data-act="play"]'); page.wait_for_timeout(700); page.click('[data-act="play"]')
        check(page.inner_text('#play') == 'Play', 'play then pause works')
        page.locator('#tree-box').scroll_into_view_if_needed()
        page.screenshot(path=os.path.join(SHOTS, f'{tag}-playground-fib.png'), full_page=False)
        page.click('#tree-py'); check("['block'," in page.inner_text('#tree-box'), 'tree python view')
        page.click('#tree-vis'); page.click('#tok-py'); check("'\\x00'" in page.inner_text('#tokens'), 'token python view shows EOF as \\x00')
        page.click('#tok-chips')
        # quirks
        page.click('[data-quirk="0"]'); page.wait_for_timeout(200)
        check('200' in page.inner_text('#results'), 'quirk: (if 5 100 200) gives 200')
        page.click('[data-quirk="2"]'); page.wait_for_timeout(200)
        check('Undefined variable: g' in page.inner_text('#results'), 'quirk: globals invisible error shown')
        page.click('[data-quirk="5"]'); page.wait_for_timeout(200)
        check('step 2, parse' in page.inner_text('#results').lower(), 'missing paren reported at parse step')
        # typing custom code and Ctrl+Enter
        page.fill('#code', '(while 1 0)')
        page.press('#code', 'Control+Enter'); page.wait_for_timeout(1500)
        check('infinite loop' in page.inner_text('#results'), 'infinite loop is stopped with message')
        check(page.input_value('#example') == 'custom', 'example menu switches to custom when typing')
        no_overflow(page, 'playground after runs')

        # ===== code walkthrough =====
        page.goto(URL + '#code'); page.wait_for_timeout(200)
        check(page.locator('.walk-row').count() == 6, 'six walkthrough sections')
        n_lines = page.locator('.py .ln').count()
        src_lines = len(open(os.path.join(ROOT, 'minilisp.py')).read().rstrip('\n').split('\n'))
        check(abs(n_lines - src_lines) <= 6, f'walkthrough shows the whole file ({n_lines} of {src_lines} lines, blank separators trimmed)')

        # ===== quiz =====
        page.goto(URL + '#quiz'); page.wait_for_timeout(200)
        check(page.locator('.q').count() == 14, 'robotics quiz has 14 questions')
        page.locator('.q').first.locator('.opt').first.click()
        check(page.locator('.q').first.locator('.q-why').count() == 1, 'answering shows explanation')
        check('answered' in page.inner_text('#score'), 'score updates')
        page.click('[data-quiz="interp"]')
        check(page.locator('.q').count() == 19, 'interpreter quiz has 19 questions')
        # answer all 19, then make sure the final score line appears
        for i in range(19):
            page.locator('.q').nth(i).locator('.opt').first.click()
        check(page.inner_text('#score').startswith('Done:'), 'finishing a quiz shows the final score')
        page.screenshot(path=os.path.join(SHOTS, f'{tag}-quiz-answered.png'))
        page.click('#quiz-reset')
        check(page.locator('.q-why').count() == 0, 'start over clears answers')
        page.screenshot(path=os.path.join(SHOTS, f'{tag}-quiz-after.png'))
        check(not errors, f'no script errors ({errors[:3]})')
        ctx.close()
    browser.close()

print(f'\n{len(failures)} failures')
sys.exit(1 if failures else 0)
