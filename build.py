'''Builds index.html from template.html, engine.js and minilisp.py.
Run from the project folder:   python3 build.py
'''
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()

def main():
    template = read('template.html')
    engine = read('engine.js')
    pysrc = read('minilisp.py')
    # Safe inside <script type="application/json">: stop "</script>" and "<!--" from ending it early
    pyjson = json.dumps(pysrc).replace('</', '<\\/').replace('<!--', '<\\!--')
    assert '/*__ENGINE__*/' in template and '__PYSRC__' in template
    assert '</script' not in engine.lower()
    page = template.replace('/*__ENGINE__*/', engine).replace('__PYSRC__', pyjson)
    # wrap in a full HTML document so it works anywhere (GitHub Pages, double click)
    cut = page.index('<header class="top">')
    page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
            'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}'
            '[hidden]{display:none!important}</style>\n'
            + page[:cut] + '</head>\n<body>\n' + page[cut:] + '\n</body>\n</html>\n')
    with open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'index.html written: {len(page.encode()):,} bytes')

if __name__ == '__main__':
    main()
