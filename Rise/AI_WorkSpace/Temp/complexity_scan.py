import os, re, json, math
from collections import Counter, defaultdict

ROOTS = [
    os.path.abspath('.'),
]

INCLUDE_EXT = {'.py', '.js', '.ts', '.vue'}
EXCLUDE_DIRS = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.venv', '.idea', '.vscode'}

LAYER_PACKAGES = ['business_logic', 'business_service', 'foundational_service', 'interface_entry', 'project_utility']

WEB_TOKENS = {'fastapi','starlette','uvicorn','router','Response','Request','WebSocket','aiogram','telegram'}
DB_TOKENS = {'pymongo','motor','MongoClient','redis','aioredis','sqlalchemy','psycopg','GridFS'}
AI_TOKENS = {'openai','anthropic','transformers','tokenizer','llm','embedding'}
INFRA_TOKENS = {'os','pathlib','subprocess','logging','rich','threading','asyncio','multiprocessing','dotenv','yaml','json'}
BUSINESS_TOKENS = {'workflow','orchestrator','policy','knowledge','snapshot','telegram_flow','channel','binding'}

def read_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ''

def max_indent_level(lines):
    maxlvl = 0
    deep_lines = 0
    code_lines = 0
    for ln in lines:
        if not ln.strip():
            continue
        code_lines += 1
        s = len(ln) - len(ln.lstrip(' '))
        lvl = s // 4
        if lvl >= 4:
            deep_lines += 1
        if lvl > maxlvl:
            maxlvl = lvl
    return maxlvl, (deep_lines / code_lines if code_lines else 0.0)

def py_metrics(text):
    lines = text.splitlines()
    total = len(lines)
    nonblank = sum(1 for l in lines if l.strip())
    imports = sum(1 for l in lines if re.match(r"\s*(from |import )", l))
    classes = [i for i,l in enumerate(lines) if re.match(r"\s*class ", l)]
    func_idxs = [i for i,l in enumerate(lines) if re.match(r"\s*(async\s+)?def ", l)]
    func_lens = []
    max_params = 0
    for idx, start in enumerate(func_idxs):
        end = func_idxs[idx+1] if idx+1 < len(func_idxs) else len(lines)
        # Stop earlier if a class starts after start and before end
        for c in classes:
            if c > start and c < end:
                end = c
                break
        func_lens.append(max(0, end - start))
        sig = lines[start]
        m = re.search(r"def\s+\w+\((.*?)\)", sig)
        if m:
            params = [p for p in m.group(1).split(',') if p.strip()]
            max_params = max(max_params, len(params))
    longest = max(func_lens) if func_lens else 0
    avg_len = sum(func_lens)/len(func_lens) if func_lens else 0.0
    # rough cyclomatic proxies
    tokens = re.findall(r"\b(if|for|while|and|or|try|except|with|elif|case)\b", text)
    decision_points = len(tokens)
    indent_max, deep_ratio = max_indent_level(lines)
    # coupling: count unique internal layer packages imported
    imported_layers = set()
    for l in lines:
        m = re.match(r"\s*from\s+src\.(.*?)\s+import", l)
        if m:
            seg = m.group(1).split('.')[0]
            if seg in LAYER_PACKAGES:
                imported_layers.add(seg)
        m2 = re.match(r"\s*import\s+src\.(.*?)", l)
        if m2:
            seg = m2.group(1).split('.')[0]
            if seg in LAYER_PACKAGES:
                imported_layers.add(seg)
    # mixed concerns categories
    categories = 0
    low = text.lower()
    if any(t in low for t in WEB_TOKENS):
        categories += 1
    if any(t in low for t in DB_TOKENS):
        categories += 1
    if any(t in low for t in AI_TOKENS):
        categories += 1
    if any(t in low for t in INFRA_TOKENS):
        categories += 1
    if any(t in low for t in BUSINESS_TOKENS):
        categories += 1
    # duplication ratio: repeated non-trivial lines
    norm_lines = [re.sub(r"\s+", " ", l.strip()) for l in lines if len(l.strip())>20]
    cnt = Counter(norm_lines)
    repeated = sum(c for c in cnt.values() if c>1)
    dup_ratio = repeated / len(norm_lines) if norm_lines else 0.0
    # boundary: presence of router + service/repository words
    boundary = 1 if (re.search(r"\b(FastAPI|APIRouter|Router)\b", text) and re.search(r"\b(Service|Repository|usecase|orchestrator)\b", text)) else 0
    return {
        'total_lines': total,
        'nonblank_lines': nonblank,
        'imports': imports,
        'classes': len(classes),
        'functions': len(func_idxs),
        'longest_func': int(longest),
        'avg_func_len': avg_len,
        'max_params': max_params,
        'decision_points': decision_points,
        'indent_max': indent_max,
        'deep_nest_ratio': deep_ratio,
        'imported_layers': len(imported_layers),
        'mixed_categories': categories,
        'dup_ratio': dup_ratio,
        'boundary_router_service': boundary,
    }

def js_metrics(text):
    lines = text.splitlines()
    total = len(lines)
    nonblank = sum(1 for l in lines if l.strip())
    # crude metrics
    functions = len(re.findall(r"\bfunction\b|=>\s*\(|\w+\s*:\s*\(.*?\)\s*=>", text))
    longest_block = 0
    depth = 0
    max_depth = 0
    deep_lines = 0
    code_lines = 0
    for l in lines:
        if not l.strip():
            continue
        code_lines += 1
        opens = l.count('{')
        closes = l.count('}')
        depth += opens
        if depth >= 6:
            deep_lines += 1
        max_depth = max(max_depth, depth)
        depth -= closes
    deep_ratio = deep_lines / code_lines if code_lines else 0.0
    imports = len(re.findall(r"^\s*import\s+|require\(", text, flags=re.M))
    # mixed concerns: UI + network + state
    categories = 0
    low = text.lower()
    if any(t in low for t in ['vue','react','template','component','ref(','computed(','watch(']):
        categories += 1
    if any(t in low for t in ['fetch(','axios','websocket','eventsource']):
        categories += 1
    if any(t in low for t in ['store','pinia','vuex','localstorage','sessionstorage']):
        categories += 1
    if any(t in low for t in ['schema','validate','zod','yup']):
        categories += 1
    dup_ratio = 0.0
    norm_lines = [re.sub(r"\s+", " ", l.strip()) for l in lines if len(l.strip())>20]
    cnt = Counter(norm_lines)
    repeated = sum(c for c in cnt.values() if c>1)
    dup_ratio = repeated / len(norm_lines) if norm_lines else 0.0
    return {
        'total_lines': total,
        'nonblank_lines': nonblank,
        'functions': functions,
        'imports': imports,
        'max_depth': max_depth,
        'deep_nest_ratio': deep_ratio,
        'mixed_categories': categories,
        'dup_ratio': dup_ratio,
    }

def score_py(m):
    s=0
    # size matters but modest weight
    if m['nonblank_lines']>800: s+=4
    elif m['nonblank_lines']>400: s+=2
    # god function
    if m['longest_func']>200: s+=5
    elif m['longest_func']>120: s+=3
    # deep nesting
    if m['deep_nest_ratio']>0.20: s+=4
    elif m['deep_nest_ratio']>0.10: s+=2
    # mixed concerns
    if m['mixed_categories']>=4: s+=5
    elif m['mixed_categories']>=3: s+=3
    # cross-layer imports
    if m['imported_layers']>=4: s+=5
    elif m['imported_layers']>=3: s+=3
    # duplication
    if m['dup_ratio']>0.40: s+=3
    elif m['dup_ratio']>0.25: s+=2
    # unclear boundary
    if m['boundary_router_service']: s+=2
    return s

def score_js(m):
    s=0
    if m['nonblank_lines']>800: s+=4
    elif m['nonblank_lines']>400: s+=2
    if m['max_depth']>=10 or m['deep_nest_ratio']>0.2: s+=4
    elif m['max_depth']>=7 or m['deep_nest_ratio']>0.1: s+=2
    if m['mixed_categories']>=3: s+=4
    elif m['mixed_categories']>=2: s+=2
    if m['dup_ratio']>0.40: s+=3
    elif m['dup_ratio']>0.25: s+=2
    return s

def iter_files():
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in INCLUDE_EXT:
                    yield os.path.join(dirpath, fn)

def main():
    results = []
    for path in iter_files():
        rel = os.path.relpath(path, os.getcwd())
        text = read_text(path)
        ext = os.path.splitext(path)[1].lower()
        if ext == '.py':
            m = py_metrics(text)
            score = score_py(m)
            rtype = 'py'
        else:
            m = js_metrics(text)
            score = score_js(m)
            rtype = 'js'
        if score>0:
            results.append({'path': rel.replace('\\', '/'), 'type': rtype, 'score': score, 'metrics': m})
    results.sort(key=lambda x: x['score'], reverse=True)
    print(json.dumps(results[:30], indent=2))

if __name__ == '__main__':
    main()

