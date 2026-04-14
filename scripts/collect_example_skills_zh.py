#!/usr/bin/env python3
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / 'examples' / 'zh-community'
TMP_DIR = ROOT / '.tmp_examples_zh'

SOURCES = [
    {
        'alias': 'tanweai-pua',
        'repo': 'tanweai/pua',
        'skills_root': 'skills',
        'include': [
            'mama', 'p10', 'p7', 'p9', 'pro', 'pua-en', 'pua-ja', 'pua-loop', 'pua', 'shot', 'yes',
        ],
    },
    {
        'alias': 'xstongxue-best-skills',
        'repo': 'xstongxue/best-skills',
        'skills_root': 'skills',
        'include': [
            'codegen-diagram', 'codegen-doc', 'dev-workflow', 'drawio-diagram', 'excalidraw-diagram',
            'md-report-summary', 'paper-write', 'pptgen-drawio', 'skill-create', 'skill-prompt-convert',
            'wechat-article-writer',
        ],
    },
    {
        'alias': 'everything-claude-code-zh',
        'repo': 'xu-xiang/everything-claude-code-zh',
        'skills_root': 'skills',
        'include': None,
    },
    {
        'alias': 'partme-full-stack-skills',
        'repo': 'partme-ai/full-stack-skills',
        'skills_root': 'skills',
        'include': [
            'angular-skills/angular',
            'antd-skills/ant-design-react',
            'build-skills/rspack',
            'database-skills/postgresql',
            'database-skills/redis',
            'design-skills/brand-guidelines',
            'devops-skills/github-actions',
            'devops-skills/kubernetes',
            'docker-skills/docker',
            'document-skills/mermaid',
            'go-skills/gin',
            'nodejs-skills/nestjs',
            'python-skills/fastapi',
            'react-skills/react',
        ],
    },
    {
        'alias': 'shareai-skills',
        'repo': 'shareAI-lab/shareAI-skills',
        'skills_root': 'skills',
        'include': ['agent-builder', 'media-writer', 'skill-judge', 'vibe-coding'],
    },
    {
        'alias': 'khazix-skills',
        'repo': 'KKKKhazix/khazix-skills',
        'skills_root': '.',
        'include': ['hv-analysis', 'khazix-writer'],
    },
]


def run(*args, cwd=None):
    res = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout


def gh_json(endpoint):
    return json.loads(run('gh', 'api', endpoint))


def list_dirs(repo, skills_root):
    endpoint = f'repos/{repo}/contents' if skills_root == '.' else f'repos/{repo}/contents/{skills_root}'
    payload = gh_json(endpoint)
    return sorted([item['name'] for item in payload if item.get('type') == 'dir'])


def repo_meta(repo):
    payload = gh_json(f'repos/{repo}')
    return {
        'full_name': payload['full_name'],
        'html_url': payload['html_url'],
        'default_branch': payload['default_branch'],
        'stargazers_count': payload['stargazers_count'],
        'description': payload.get('description') or '',
    }


def clone_repo(repo, dest):
    if dest.exists():
        shutil.rmtree(dest)
    run('git', 'clone', '--depth', '1', f'https://github.com/{repo}.git', str(dest))


def skill_source_path(clone_path, skills_root, skill_name):
    return clone_path / skill_name if skills_root == '.' else clone_path / skills_root / skill_name


def skill_source_url(meta, skills_root, skill_name):
    if skills_root == '.':
        return f"{meta['html_url']}/tree/{meta['default_branch']}/{skill_name}"
    return f"{meta['html_url']}/tree/{meta['default_branch']}/{skills_root}/{skill_name}"


def main():
    if EXAMPLES_DIR.exists():
        shutil.rmtree(EXAMPLES_DIR)
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    index = []
    source_counts = {}

    for source in SOURCES:
        repo = source['repo']
        alias = source['alias']
        skills_root = source['skills_root']
        include = source['include']

        if include is None:
            selected = sorted(list_dirs(repo, skills_root))
            missing = []
        else:
            selected = []
            missing = []
            for name in include:
                endpoint = f'repos/{repo}/contents/{name}' if skills_root == '.' else f'repos/{repo}/contents/{skills_root}/{name}'
                check = subprocess.run(['gh', 'api', endpoint], capture_output=True, text=True)
                if check.returncode == 0:
                    selected.append(name)
                else:
                    missing.append(name)
        if missing:
            print(f'[WARN] missing in {repo}: {missing}')

        meta = repo_meta(repo)
        clone_path = TMP_DIR / alias
        clone_repo(repo, clone_path)

        out_dir = EXAMPLES_DIR / alias
        out_dir.mkdir(parents=True, exist_ok=True)
        source_counts[alias] = 0

        for name in selected:
            src = skill_source_path(clone_path, skills_root, name)
            local_name = name.replace('/', '__')
            dst = out_dir / local_name

            actual_src = src
            if not (actual_src / 'SKILL.md').exists():
                nested = [d for d in actual_src.iterdir() if d.is_dir() and (d / 'SKILL.md').exists()] if actual_src.exists() else []
                if len(nested) == 1:
                    actual_src = nested[0]
                else:
                    print(f'[SKIP] no SKILL.md: {src}')
                    continue

            shutil.copytree(actual_src, dst)
            source_counts[alias] += 1
            index.append({
                'name': local_name,
                'upstream_name': name,
                'source_alias': alias,
                'repo': meta['full_name'],
                'repo_url': meta['html_url'],
                'repo_stars': meta['stargazers_count'],
                'repo_description': meta['description'],
                'source_path': name if skills_root == '.' else f'{skills_root}/{name}',
                'source_url': skill_source_url(meta, skills_root, name),
                'local_path': str(dst.relative_to(ROOT)),
                'community': 'zh',
            })

    index.sort(key=lambda x: (x['source_alias'], x['name']))
    (EXAMPLES_DIR / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')

    lines = [
        '# Chinese Community Skills Collection',
        '',
        'This directory contains around 100 publicly available skills collected from Chinese community repositories for SkillLint testing and evaluation.',
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
        '- Machine-readable index: `examples/zh-community/index.json`',
    ])
    (EXAMPLES_DIR / 'README.md').write_text('\n'.join(lines) + '\n')

    print(f'Collected {len(index)} Chinese community skills into {EXAMPLES_DIR}')
    for alias, count in sorted(source_counts.items()):
        print(f'  {alias}: {count}')

if __name__ == '__main__':
    main()
