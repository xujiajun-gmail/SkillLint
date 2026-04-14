from skilllint.utils.language import detect_report_language


def test_detect_report_language_zh() -> None:
    assert detect_report_language("这是一个技能说明文档，用于自动生成中文报告。") == "zh"


def test_detect_report_language_en() -> None:
    assert detect_report_language("This is a skill description used to produce an English report.") == "en"
