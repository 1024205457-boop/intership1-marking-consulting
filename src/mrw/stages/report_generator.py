"""ReportGenerator — Jinja2 模板生成 HTML 报告"""

import json
from pathlib import Path
from jinja2 import Template


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{ title }} - 洞察报告</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }
        h1 { color: #1a1a1a; border-bottom: 2px solid #007aff; padding-bottom: 10px; }
        h2 { color: #444; margin-top: 30px; }
        .insight-card { background: #f8f9fa; border-left: 4px solid #007aff; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }
        .insight-card.high { border-left-color: #28a745; }
        .insight-card.medium { border-left-color: #ffc107; }
        .insight-card.low { border-left-color: #dc3545; }
        .confidence { font-size: 12px; color: #666; margin-top: 4px; }
        .summary { background: #e8f4fd; padding: 16px; border-radius: 8px; margin: 20px 0; }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; }
        .stat-item { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007aff; }
        .stat-label { font-size: 12px; color: #666; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>品类：{{ category }} | 样本量：{{ sample_size }} 条</p>

    <div class="summary">
        <h2>验证概览</h2>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{{ validation.summary.total }}</div>
                <div class="stat-label">总洞察数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ validation.summary.high }}</div>
                <div class="stat-label">高置信</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ validation.summary.medium }}</div>
                <div class="stat-label">中置信</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ validation.summary.low }}</div>
                <div class="stat-label">低置信（待复核）</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ "%.0f"|format(validation.summary.pass_rate * 100) }}%</div>
                <div class="stat-label">通过率</div>
            </div>
        </div>
    </div>

    <h2>痛点洞察</h2>
    {% for result in validation.results %}
    <div class="insight-card {{ result.level }}">
        <strong>{{ result.content }}</strong>
        <div class="confidence">
            置信度：{{ result.final_confidence }} ({{ result.level }}) |
            来源：{{ result.source_check.valid_sources|default(0) }} 条原声 |
            处理：{{ result.action }}
        </div>
    </div>
    {% endfor %}

    <h2>决策路径</h2>
    <p>{{ decision_path | join(" → ") }}</p>

    <h2>建议</h2>
    <ul>
    {% for rec in recommendations %}
        <li>{{ rec }}</li>
    {% endfor %}
    </ul>

    <hr>
    <p style="font-size: 12px; color: #999;">
        由 AI 辅助市场研究工作流自动生成 | 三元校验通过率 {{ "%.0f"|format(validation.summary.pass_rate * 100) }}%
    </p>
</body>
</html>"""


def generate_report(
    research_goal: dict,
    analysis: dict,
    validation: dict,
    output_dir: str,
) -> str:
    """
    生成 HTML 洞察报告。

    Args:
        research_goal: 结构化研究目标
        analysis: 框架分析结果
        validation: 三元校验结果
        output_dir: 输出目录

    Returns:
        报告文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    template = Template(REPORT_TEMPLATE)
    html = template.render(
        title=research_goal.get("title", "研究报告"),
        category=research_goal.get("category", ""),
        sample_size=analysis["persona"]["sample_size"],
        validation=validation,
        decision_path=analysis.get("decision_path", []),
        recommendations=analysis.get("recommendations", []),
    )

    report_path = output_path / "report.html"
    report_path.write_text(html, encoding="utf-8")

    # 同时输出结构化 JSON
    insights_path = output_path / "insights.json"
    insights_path.write_text(
        json.dumps(analysis["insights"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    validation_path = output_path / "validation_report.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(report_path)
