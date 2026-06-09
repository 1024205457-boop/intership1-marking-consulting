"""测试 TripleValidator"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mrw.stages.triple_validator import validate


@pytest.fixture
def sample_comments():
    return [
        {"id": "c001", "text": "价格太贵了买不起", "sentiment": "negative", "source": "小红书"},
        {"id": "c002", "text": "贵是贵但效果好", "sentiment": "negative", "source": "抖音"},
        {"id": "c003", "text": "性价比不高太贵了", "sentiment": "negative", "source": "知乎"},
        {"id": "c004", "text": "质量很好推荐", "sentiment": "positive", "source": "天猫"},
        {"id": "c005", "text": "回购了很满意", "sentiment": "positive", "source": "京东"},
    ]


def test_source_check_pass(sample_comments):
    insights = [{
        "id": "i001",
        "content": "用户认为价格太贵",
        "source_ids": ["c001", "c002", "c003"],
        "confidence": 0.8,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["source_check"]["passed"] is True
    assert result["results"][0]["source_check"]["valid_sources"] == 3


def test_source_check_fail_no_ids(sample_comments):
    insights = [{
        "id": "i001",
        "content": "没有来源的洞察",
        "source_ids": [],
        "confidence": 0.5,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["source_check"]["passed"] is False


def test_source_check_fail_invalid_ids(sample_comments):
    insights = [{
        "id": "i001",
        "content": "来源不存在的洞察",
        "source_ids": ["invalid_001", "invalid_002"],
        "confidence": 0.5,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["source_check"]["passed"] is False


def test_cross_check_consistent(sample_comments):
    insights = [{
        "id": "i001",
        "content": "价格贵",
        "source_ids": ["c001", "c002", "c003"],
        "confidence": 0.8,
    }]
    result = validate(insights, sample_comments)
    cross = result["results"][0]["cross_check"]
    assert cross["passed"] is True
    assert cross["consistency"] == 1.0


def test_cross_check_insufficient_sources(sample_comments):
    insights = [{
        "id": "i001",
        "content": "单条洞察",
        "source_ids": ["c001"],
        "confidence": 0.5,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["cross_check"]["passed"] is False


def test_logic_check_overgeneralization(sample_comments):
    insights = [{
        "id": "i001",
        "content": "100%的用户都觉得贵",
        "source_ids": ["c001", "c002"],
        "confidence": 0.8,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["logic_check"]["passed"] is False


def test_logic_check_pass(sample_comments):
    insights = [{
        "id": "i001",
        "content": "部分用户反馈价格偏高",
        "source_ids": ["c001", "c002", "c003"],
        "confidence": 0.8,
    }]
    result = validate(insights, sample_comments)
    assert result["results"][0]["logic_check"]["passed"] is True


def test_confidence_levels(sample_comments):
    insights = [
        {
            "id": "i001",
            "content": "价格贵",
            "source_ids": ["c001", "c002", "c003"],
            "confidence": 0.8,
        },
        {
            "id": "i002",
            "content": "单源洞察",
            "source_ids": ["c004"],
            "confidence": 0.4,
        },
    ]
    result = validate(insights, sample_comments)
    assert result["results"][0]["level"] in ("high", "medium")
    assert result["results"][1]["level"] == "low"
    assert result["summary"]["pass_rate"] == 0.5


def test_validation_summary(sample_comments):
    insights = [{
        "id": "i001",
        "content": "价格贵",
        "source_ids": ["c001", "c002", "c003"],
        "confidence": 0.8,
    }]
    result = validate(insights, sample_comments)
    summary = result["summary"]
    assert "total" in summary
    assert "pass_rate" in summary
    assert "avg_confidence" in summary
    assert summary["total"] == 1
