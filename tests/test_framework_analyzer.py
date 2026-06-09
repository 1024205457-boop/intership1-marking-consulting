"""测试 FrameworkAnalyzer"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mrw.stages.framework_analyzer import (
    analyze,
    _extract_persona,
    _extract_pain_points_nlp,
    _extract_decision_path,
    _is_negative_by_rule,
)


@pytest.fixture
def sample_comments():
    return [
        {"id": "c001", "text": "这个奶粉太贵了买不起", "sentiment": "negative", "source": "抖音"},
        {"id": "c002", "text": "价格贵但配方确实好", "sentiment": "negative", "source": "小红书"},
        {"id": "c003", "text": "性价比不高太贵了", "sentiment": "negative", "source": "知乎"},
        {"id": "c004", "text": "宝宝喝了过敏起湿疹", "sentiment": "negative", "source": "天猫"},
        {"id": "c005", "text": "过敏了退货", "sentiment": "negative", "source": "京东"},
        {"id": "c006", "text": "听朋友推荐买的挺好", "sentiment": "positive", "source": "妈妈群"},
        {"id": "c007", "text": "搜了很多测评对比才选的", "sentiment": "positive", "source": "小红书"},
        {"id": "c008", "text": "回购第三罐了很满意", "sentiment": "positive", "source": "天猫"},
        {"id": "c009", "text": "在直播间下单的有赠品", "sentiment": "positive", "source": "抖音"},
        {"id": "c010", "text": "推荐给同事了她也觉得好", "sentiment": "positive", "source": "小红书"},
    ]


@pytest.fixture
def sample_research_goal():
    return {
        "title": "奶粉消费者研究",
        "category": "婴幼儿配方奶粉",
        "keywords": ["贵", "过敏", "配方"],
        "dimensions": ["价格", "安全性"],
    }


def test_is_negative_by_rule():
    assert _is_negative_by_rule("太贵了买不起") is True
    assert _is_negative_by_rule("过敏了很难受") is True
    assert _is_negative_by_rule("很好用推荐") is False
    assert _is_negative_by_rule("一般般") is False


def test_extract_persona(sample_comments):
    persona = _extract_persona(sample_comments)
    assert persona["sample_size"] == 10
    assert "positive" in persona["sentiment_distribution"]
    assert "negative" in persona["sentiment_distribution"]
    assert persona["source_distribution"]["小红书"] == 3
    assert len(persona["top_concerns"]) > 0


def test_extract_pain_points_nlp(sample_comments):
    pain_points = _extract_pain_points_nlp(sample_comments, ["贵", "过敏"])
    assert len(pain_points) > 0
    # 每个痛点应该有 source_ids
    for pp in pain_points:
        assert "source_ids" in pp
        assert "confidence" in pp
        assert len(pp["source_ids"]) >= 1


def test_extract_decision_path(sample_comments):
    path = _extract_decision_path(sample_comments)
    assert len(path) > 0
    # 至少应该有购买阶段（"回购""下单"）
    stages = [p["stage"] for p in path]
    assert any("购买" in s for s in stages)


def test_analyze_full(sample_comments, sample_research_goal):
    """测试完整分析流程（无 LLM，走 fallback）"""
    result = analyze(sample_comments, sample_research_goal)

    assert "persona" in result
    assert "pain_points" in result
    assert "decision_path" in result
    assert "recommendations" in result
    assert "insights" in result

    # 洞察应该有 source_ids
    for insight in result["insights"]:
        assert "id" in insight
        assert "source_ids" in insight
        assert "confidence" in insight


def test_analyze_empty_comments(sample_research_goal):
    result = analyze([], sample_research_goal)
    assert result["persona"]["sample_size"] == 0
    assert result["insights"] == []
