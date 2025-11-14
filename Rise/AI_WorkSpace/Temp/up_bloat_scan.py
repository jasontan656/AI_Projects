import json
import re
from pathlib import Path

up_root = Path('D:/AI_Projects/Up')
skip_dirs = {'AI_WorkSpace', '.git', 'node_modules', 'dist', 'build', '.vite', '.nuxt', '.cache'}

results = []

metrics_patterns = {
    'watchers': re.compile(r'\bwatch\b'),
    'computeds': re.compile(r'\bcomputed\b'),
    'stores': re.compile(r'\bstore\b|\bpinia\b', re.IGNORECASE),
    'emits': re.compile(r'\$emit|emit\('),
    'forms': re.compile(r'ElForm|form\b', re.IGNORECASE),
    'services': re.compile(r'service', re.IGNORECASE),
}

def should_skip(path: Path) -> bool:
    return any(part in skip_dirs for part in path.parts)

for path in up_root.rglob('*'):
    if should_skip(path):
        continue
    if path.suffix not in {'.vue', '.js'}:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        continue
    if not text.strip():
        continue
    lines = text.count('\n') + 1
    import_count = len([line for line in text.splitlines() if line.strip().startswith('import ')])
    export_count = text.count('export default') + text.count('module.exports') + text.count('export function')
    template_blocks = text.count('<template')
    script_blocks = text.count('<script') if path.suffix == '.vue' else 0
    style_blocks = text.count('<style') if path.suffix == '.vue' else 0
    metrics = {name: len(pattern.findall(text)) for name, pattern in metrics_patterns.items()}
    reactive_features = metrics['watchers'] + metrics['computeds'] + metrics['stores']
    eventfulness = metrics['emits']
    forms = metrics['forms']
    service_refs = metrics['services']
    duplication_penalty = 1 if 'TODO' in text or text.count('http') > 5 else 0
    mix_penalty = 0
    if reactive_features > 5 and eventfulness > 5:
        mix_penalty += 1
    if forms and service_refs:
        mix_penalty += 0.5
    score = (
        lines / 200 +
        import_count / 20 +
        export_count / 10 +
        reactive_features / 15 +
        eventfulness / 12 +
        forms / 20 +
        service_refs / 25 +
        template_blocks * 0.5 +
        script_blocks * 0.3 +
        style_blocks * 0.1 +
        duplication_penalty +
        mix_penalty
    )
    results.append({
        'path': str(path.relative_to(up_root)),
        'lines': lines,
        'imports': import_count,
        'reactive_features': reactive_features,
        'eventfulness': eventfulness,
        'forms': forms,
        'services': service_refs,
        'score': round(score, 3)
    })

results.sort(key=lambda x: x['score'], reverse=True)
for item in results[:30]:
    print(json.dumps(item, ensure_ascii=False))
