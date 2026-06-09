"""DataCollector — 通过 Adapter 接口加载数据"""

import json
from pathlib import Path
from typing import Protocol


class DataCollectorAdapter(Protocol):
    """数据采集适配器接口，Phase 2 可扩展为爬虫/API"""

    def collect(self, keywords: list[str], limit: int) -> list[dict]:
        ...


class JsonFileAdapter:
    """从本地 JSON 文件加载数据（Phase 1 默认）"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def collect(self, keywords: list[str], limit: int = 100) -> list[dict]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = data.get("comments", data.get("data", []))

        return data[:limit]


def collect_data(data_path: str, keywords: list[str] = None, limit: int = 100) -> list[dict]:
    """
    加载原始数据。

    Args:
        data_path: 数据文件路径（JSON）
        keywords: 过滤关键词（可选）
        limit: 最大条数

    Returns:
        原始评论/舆情列表
    """
    adapter = JsonFileAdapter(data_path)
    comments = adapter.collect(keywords or [], limit)

    # 标准化字段
    standardized = []
    for i, item in enumerate(comments):
        standardized.append({
            "id": item.get("id", f"comment_{i+1:03d}"),
            "text": item.get("text", item.get("content", "")),
            "source": item.get("source", "unknown"),
            "sentiment": item.get("sentiment", None),
            "timestamp": item.get("timestamp", None),
        })

    return standardized
