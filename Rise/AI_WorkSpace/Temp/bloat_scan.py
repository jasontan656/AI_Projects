import ast, json
from pathlib import Path

rise_root = Path('D:/ai_projects/rise')
up_root = Path('D:/AI_Projects/Up')
skip_dirs = {'AI_WorkSpace', '.git', '.mypy_cache', '.venv', 'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache'}

results = []

def should_skip(path: Path) -> bool:
    return any(part in skip_dirs for part in path.parts)

def analyze_python(path: Path, repo_root: Path, repo: str):
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return
    if not text.strip():
        return
    try:
        tree = ast.parse(text)
    except Exception:
        return
    total_lines = text.count('\n') + 1
    import_lines = sum(1 for line in text.splitlines() if line.strip().startswith(('import ', 'from ')))
    funcs = []
    classes = []
    assignments = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, 'end_lineno', node.lineno)
            funcs.append(max(0, end - node.lineno + 1))
        elif isinstance(node, ast.ClassDef):
            end = getattr(node, 'end_lineno', node.lineno)
            classes.append(max(0, end - node.lineno + 1))
        elif isinstance(node, ast.Assign):
            assignments += 1
    max_func = max(funcs) if funcs else 0
    max_class = max(classes) if classes else 0
    mix_penalty = 1 if funcs and classes else 0
    large_func_penalty = max(0, (max_func - 80) / 120)
    large_class_penalty = max(0, (max_class - 200) / 200)
    avg_func = sum(funcs)/len(funcs) if funcs else 0
    heterogeneity = 0
    if funcs and classes:
        heterogeneity += 0.5
    if assignments > (len(funcs) + len(classes))*2:
        heterogeneity += 0.3
    score = (
        total_lines / 300 +
        len(funcs) / 10 +
        len(classes) / 8 +
        mix_penalty +
        large_func_penalty +
        large_class_penalty +
        import_lines / 80 +
        assignments / 400 +
        avg_func / 200 +
        heterogeneity
    )
    results.append({
        'repo': repo,
        'path': str(path.relative_to(repo_root)),
        'lines': total_lines,
        'functions': len(funcs),
        'classes': len(classes),
        'max_func': max_func,
        'max_class': max_class,
        'imports': import_lines,
        'score': round(score, 3)
    })

def walk_python(root: Path, repo: str):
    for path in root.rglob('*.py'):
        if should_skip(path):
            continue
        analyze_python(path, root, repo)

walk_python(rise_root, 'rise')
walk_python(up_root, 'up')

results.sort(key=lambda x: x['score'], reverse=True)
for item in results[:40]:
    print(json.dumps(item, ensure_ascii=False))
