import json
from pathlib import Path

from skilllint.baseline import (
    build_baseline_dataset,
    load_example_targets,
    render_baseline_markdown,
)


def test_load_example_targets_reads_general_and_zh_indexes(tmp_path: Path) -> None:
    examples_dir = tmp_path / 'examples'
    zh_dir = examples_dir / 'zh-community'
    examples_dir.mkdir(parents=True)
    zh_dir.mkdir(parents=True)

    (examples_dir / 'index.json').write_text(
        json.dumps([
            {
                'name': 'alpha',
                'source_alias': 'src-a',
                'local_path': 'examples/src-a/alpha',
            }
        ]),
        encoding='utf-8',
    )
    (zh_dir / 'index.json').write_text(
        json.dumps([
            {
                'name': 'beta',
                'source_alias': 'src-b',
                'local_path': 'examples/zh-community/src-b/beta',
                'community': 'zh',
            }
        ]),
        encoding='utf-8',
    )

    targets = load_example_targets(tmp_path)
    assert [target.name for target in targets] == ['alpha', 'beta']
    assert targets[1].community == 'zh'



def test_build_baseline_dataset_scans_fixture_corpus(tmp_path: Path) -> None:
    examples_dir = tmp_path / 'examples'
    zh_dir = examples_dir / 'zh-community'
    skill_a = examples_dir / 'src-a' / 'alpha'
    skill_b = zh_dir / 'src-b' / 'beta'
    skill_a.mkdir(parents=True)
    skill_b.mkdir(parents=True)
    (skill_a / 'SKILL.md').write_text('Always do this before responding.', encoding='utf-8')
    (skill_b / 'SKILL.md').write_text('这是一个只读技能。', encoding='utf-8')

    (examples_dir / 'index.json').write_text(
        json.dumps([
            {
                'name': 'alpha',
                'source_alias': 'src-a',
                'local_path': 'examples/src-a/alpha',
            }
        ]),
        encoding='utf-8',
    )
    zh_dir.mkdir(parents=True, exist_ok=True)
    (zh_dir / 'index.json').write_text(
        json.dumps([
            {
                'name': 'beta',
                'source_alias': 'src-b',
                'local_path': 'examples/zh-community/src-b/beta',
                'community': 'zh',
            }
        ]),
        encoding='utf-8',
    )

    dataset = build_baseline_dataset(tmp_path, profile='balanced')

    assert dataset['sample_count'] == 2
    assert dataset['failure_count'] == 0
    assert dataset['summary']['risk_levels']['high'] >= 1
    assert dataset['community_stats']['general']['samples'] == 1
    assert dataset['community_stats']['zh']['samples'] == 1
    markdown = render_baseline_markdown(dataset)
    assert 'SkillLint Example Baseline' in markdown
    assert 'Top Risky Samples' in markdown
