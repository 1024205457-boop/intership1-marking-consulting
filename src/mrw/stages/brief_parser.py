"""BriefParser — 解析 YAML Brief，输出结构化研究目标"""

import yaml
from pathlib import Path


def parse_brief(brief_path: str) -> dict:
    """
    解析 YAML Brief 文件，提取研究目标、目标人群、关注维度。

    Args:
        brief_path: Brief YAML 文件路径

    Returns:
        结构化研究目标字典
    """
    with open(brief_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    research_goal = {
        "title": raw.get("title", ""),
        "category": raw.get("category", ""),
        "objectives": raw.get("objectives", []),
        "target_audience": raw.get("target_audience", {}),
        "dimensions": raw.get("dimensions", []),
        "keywords": raw.get("keywords", []),
    }

    # 验证必要字段
    if not research_goal["title"]:
        raise ValueError("Brief 缺少 title 字段")
    if not research_goal["objectives"]:
        raise ValueError("Brief 缺少 objectives 字段")

    return research_goal
