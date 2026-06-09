"""TripleValidator — 源校验/交叉校验/逻辑校验

逻辑校验支持 LLM 辅助判断推理链是否跳跃，无 API Key 时 fallback 到正则规则。
"""

import re
import logging
from typing import Optional

from ..llm import chat_completion, extract_json

logger = logging.getLogger(__name__)


def validate(insights: list[dict], comments: list[dict]) -> dict:
    """
    对洞察列表执行三元校验。

    Args:
        insights: 洞察列表（含 source_ids）
        comments: 原始评论数据

    Returns:
        校验报告
    """
    comment_index = {c["id"]: c for c in comments}
    results = []

    for insight in insights:
        source_result = _source_check(insight, comment_index)
        cross_result = _cross_check(insight, comment_index)
        logic_result = _logic_check(insight, comment_index)

        # 综合置信度
        checks_passed = sum([
            source_result["passed"],
            cross_result["passed"],
            logic_result["passed"],
        ])

        confidence = insight.get("confidence", 0.5)
        if checks_passed == 3:
            final_confidence = min(confidence + 0.1, 0.95)
        elif checks_passed == 2:
            final_confidence = confidence
        else:
            final_confidence = max(confidence - 0.2, 0.1)

        # 分级
        if final_confidence >= 0.75:
            level = "high"
        elif final_confidence >= 0.5:
            level = "medium"
        else:
            level = "low"

        results.append({
            "insight_id": insight["id"],
            "content": insight["content"],
            "source_check": source_result,
            "cross_check": cross_result,
            "logic_check": logic_result,
            "checks_passed": checks_passed,
            "final_confidence": round(final_confidence, 2),
            "level": level,
            "action": _get_action(level),
        })

    # 汇总统计
    total = len(results)
    summary = {
        "total": total,
        "high": sum(1 for r in results if r["level"] == "high"),
        "medium": sum(1 for r in results if r["level"] == "medium"),
        "low": sum(1 for r in results if r["level"] == "low"),
        "pass_rate": round(
            sum(1 for r in results if r["level"] != "low") / max(total, 1), 2
        ),
        "avg_confidence": round(
            sum(r["final_confidence"] for r in results) / max(total, 1), 2
        ),
    }

    return {"results": results, "summary": summary}


def _source_check(insight: dict, comment_index: dict) -> dict:
    """源校验：洞察是否绑定了有效的 source_id，原声是否语义相关"""
    source_ids = insight.get("source_ids", [])

    if not source_ids:
        return {"passed": False, "reason": "无 source_id 绑定", "valid_sources": 0}

    valid_ids = [sid for sid in source_ids if sid in comment_index]
    if not valid_ids:
        return {"passed": False, "reason": "source_id 在原始数据中不存在", "valid_sources": 0}

    # 语义相关性检查：洞察内容的关键词是否在原声中出现
    insight_content = insight.get("content", "")
    import jieba
    insight_words = set(w for w in jieba.cut(insight_content) if len(w) >= 2)

    relevant_count = 0
    for sid in valid_ids:
        comment_text = comment_index[sid].get("text", "")
        comment_words = set(w for w in jieba.cut(comment_text) if len(w) >= 2)
        overlap = insight_words & comment_words
        if len(overlap) >= 1:
            relevant_count += 1

    relevance_ratio = relevant_count / len(valid_ids) if valid_ids else 0

    return {
        "passed": True,
        "valid_sources": len(valid_ids),
        "total_sources": len(source_ids),
        "semantic_relevance": round(relevance_ratio, 2),
    }


def _cross_check(insight: dict, comment_index: dict) -> dict:
    """交叉校验：同主题多条原声情感方向是否一致"""
    source_ids = insight.get("source_ids", [])
    if len(source_ids) < 2:
        return {"passed": False, "reason": "原声不足2条，无法交叉验证"}

    sentiments = []
    sources_set = set()
    for sid in source_ids:
        if sid in comment_index:
            c = comment_index[sid]
            s = c.get("sentiment")
            if s:
                sentiments.append(s)
            sources_set.add(c.get("source", "unknown"))

    if not sentiments:
        # 无情感标注，但多源则通过
        if len(sources_set) >= 2:
            return {"passed": True, "reason": "多数据源交叉确认", "source_diversity": len(sources_set)}
        return {"passed": True, "reason": "无情感标注，跳过交叉检验"}

    # 情感一致性
    dominant = max(set(sentiments), key=sentiments.count)
    consistency = sentiments.count(dominant) / len(sentiments)

    # 数据源多样性加分
    source_diversity = len(sources_set)

    if consistency >= 0.6:
        return {
            "passed": True,
            "consistency": round(consistency, 2),
            "source_diversity": source_diversity,
            "dominant_sentiment": dominant,
        }
    else:
        return {
            "passed": False,
            "reason": f"情感方向不一致（一致性{consistency:.0%}）",
            "consistency": round(consistency, 2),
        }


def _logic_check(insight: dict, comment_index: dict) -> dict:
    """
    逻辑校验：检测过度推断。
    优先使用 LLM 判断，fallback 到正则规则。
    """
    content = insight.get("content", "")

    # 尝试 LLM 逻辑校验
    llm_result = _logic_check_llm(insight, comment_index)
    if llm_result is not None:
        return llm_result

    # Fallback: 正则规则
    return _logic_check_rule(content)


def _logic_check_llm(insight: dict, comment_index: dict) -> Optional[dict]:
    """LLM 辅助逻辑校验"""
    content = insight.get("content", "")
    source_ids = insight.get("source_ids", [])

    # 取前3条原声作为证据
    evidences = []
    for sid in source_ids[:3]:
        if sid in comment_index:
            evidences.append(comment_index[sid].get("text", ""))

    if not evidences:
        return None

    prompt = f"""请判断以下洞察结论是否存在逻辑问题。

洞察结论：{content}

支撑原声（共{len(insight.get('source_ids', []))}条，展示前3条）：
{chr(10).join(f'- {e}' for e in evidences)}

请判断：
1. 结论是否存在过度推断（从少量样本泛化为普遍结论）
2. 推理链是否有跳跃（原声→结论之间是否缺少逻辑环节）
3. 是否存在因果倒置或相关性误判

输出 JSON：
```json
{{"passed": true/false, "issues": ["问题描述"], "severity": "none/low/high"}}
```"""

    response = chat_completion(prompt, temperature=0.1, max_tokens=300)
    if not response:
        return None

    data = extract_json(response)
    if not data:
        return None

    passed = data.get("passed", True)
    issues = data.get("issues", [])

    if passed:
        return {"passed": True, "method": "llm"}
    else:
        return {
            "passed": False,
            "reason": "; ".join(issues) if issues else "LLM 检测到逻辑问题",
            "method": "llm",
        }


def _logic_check_rule(content: str) -> dict:
    """规则引擎逻辑校验"""
    overgeneralization_patterns = [
        (r"100%", "使用了绝对比例"),
        (r"所有用户|所有人|所有消费者", "使用了「所有」泛化"),
        (r"必然|一定会|肯定会", "使用了必然性断言"),
        (r"绝对|每个人|全部都", "使用了绝对化表述"),
        (r"从不|永远不|没有人", "使用了绝对否定"),
    ]

    for pattern, description in overgeneralization_patterns:
        if re.search(pattern, content):
            return {
                "passed": False,
                "reason": f"过度推断: {description}（匹配: {pattern}）",
                "method": "rule",
            }

    return {"passed": True, "method": "rule"}


def _get_action(level: str) -> str:
    """根据置信度等级返回处理方式"""
    actions = {
        "high": "直接进入报告",
        "medium": "进入报告，标注置信度",
        "low": "进入人工复核队列",
    }
    return actions.get(level, "未知")
