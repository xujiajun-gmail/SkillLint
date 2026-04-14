#!/usr/bin/env python3
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / 'examples'
TMP_DIR = ROOT / '.tmp_examples'

SOURCES = [
    {
        'alias': 'openai',
        'repo': 'openai/skills',
        'skills_root': 'skills/.curated',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'openai-system',
        'repo': 'openai/skills',
        'skills_root': 'skills/.system',
        'include': None,
        'exclude': {'openai-docs'},  # already included from .curated
    },
    {
        'alias': 'vercel-labs',
        'repo': 'vercel-labs/agent-skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'antfu',
        'repo': 'antfu/skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'apify',
        'repo': 'apify/agent-skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'callstack',
        'repo': 'callstackincubator/agent-skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'skillcreatorai',
        'repo': 'skillcreatorai/Ai-Agent-Skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
    {
        'alias': 'obsidian',
        'repo': 'kepano/obsidian-skills',
        'skills_root': 'skills',
        'include': None,
        'exclude': set(),
    },
]


def run(*args, cwd=None):
    res = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout


def gh_json(endpoint):
    out = run('gh', 'api', endpoint)
    return json.loads(out)


def list_skill_dirs(repo: str, skills_root: str):
    payload = gh_json(f'repos/{repo}/contents/{skills_root}')
    return sorted([item['name'] for item in payload if item.get('type') == 'dir'])


def repo_meta(repo: str):
    payload = gh_json(f'repos/{repo}')
    return {
        'full_name': payload['full_name'],
        'html_url': payload['html_url'],
        'default_branch': payload['default_branch'],
        'stargazers_count': payload['stargazers_count'],
        'description': payload.get('description') or '',
    }


def clone_repo(repo: str, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    run('git', 'clone', '--depth', '1', f'https://github.com/{repo}.git', str(dest))


def copy_skill(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    index = []

    for source in SOURCES:
        repo = source['repo']
        alias = source['alias']
        skills_root = source['skills_root']
        names = list_skill_dirs(repo, skills_root)
        if source['include']:
            include_set = set(source['include'])
            names = [n for n in names if n in include_set]
        names = [n for n in names if n not in source['exclude']]

        meta = repo_meta(repo)
        clone_path = TMP_DIR / alias
        clone_repo(repo, clone_path)

        source_out = EXAMPLES_DIR / alias
        source_out.mkdir(parents=True, exist_ok=True)

        for name in names:
            src = clone_path / skills_root / name
            if not src.exists():
                print(f'[WARN] missing {repo}:{skills_root}/{name}')
                continue
            dst = source_out / name
            copy_skill(src, dst)
            index.append({
                'name': name,
                'source_alias': alias,
                'repo': meta['full_name'],
                'repo_url': meta['html_url'],
                'repo_stars': meta['stargazers_count'],
                'repo_description': meta['description'],
                'source_path': f'{skills_root}/{name}',
                'source_url': f"{meta['html_url']}/tree/{meta['default_branch']}/{skills_root}/{name}",
                'local_path': str(dst.relative_to(ROOT)),
            })

    index.sort(key=lambda x: (x['source_alias'], x['name']))
    (EXAMPLES_DIR / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')

    source_counts = {}
    for item in index:
        source_counts[item['source_alias']] = source_counts.get(item['source_alias'], 0) + 1

    lines = [
        '# Example Skills Collection',
        '',
        'This directory contains roughly 100 publicly available agent skills collected from popular or official repositories for SkillLint testing and evaluation.',
        '',
        '## Sources',
        '',
    ]
    for source in SOURCES:
        alias = source['alias']
        count = source_counts.get(alias, 0)
        if count == 0:
            continue
        sample = next(item for item in index if item['source_alias'] == alias)
        lines.extend([
            f'- **{alias}**: {count} skills',
            f'  - repo: `{sample["repo"]}`',
            f'  - url: {sample["repo_url"]}',
            f'  - stars: {sample["repo_stars"]}',
        ])
    lines.extend([
        '',
        '## Total',
        '',
        f'- {len(index)} skills',
        '',
        '## Index',
        '',
        '- Machine-readable index: `examples/index.json`',
    ])
    (EXAMPLES_DIR / 'README.md').write_text('\n'.join(lines) + '\n')

    print(f'Collected {len(index)} skills into {EXAMPLES_DIR}')
    for alias, count in sorted(source_counts.items()):
        print(f'  {alias}: {count}')


if __name__ == '__main__':
    main()
