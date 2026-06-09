"""测试 BriefParser"""

import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mrw.stages.brief_parser import parse_brief


@pytest.fixture
def sample_brief(tmp_path):
    content = """
title: 测试研究
category: 测试品类
objectives:
  - 目标1
  - 目标2
target_audience:
  age: 25-35
dimensions:
  - 维度1
keywords:
  - 关键词1
  - 关键词2
"""
    brief_file = tmp_path / "test_brief.yaml"
    brief_file.write_text(content, encoding="utf-8")
    return str(brief_file)


def test_parse_brief_basic(sample_brief):
    result = parse_brief(sample_brief)
    assert result["title"] == "测试研究"
    assert result["category"] == "测试品类"
    assert len(result["objectives"]) == 2
    assert result["keywords"] == ["关键词1", "关键词2"]


def test_parse_brief_missing_title(tmp_path):
    content = """
category: 测试
objectives:
  - 目标1
"""
    brief_file = tmp_path / "bad_brief.yaml"
    brief_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="title"):
        parse_brief(str(brief_file))


def test_parse_brief_missing_objectives(tmp_path):
    content = """
title: 有标题但没目标
category: 测试
"""
    brief_file = tmp_path / "bad_brief2.yaml"
    brief_file.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="objectives"):
        parse_brief(str(brief_file))
