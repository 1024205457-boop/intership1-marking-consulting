"""FrameworkAnalyzer — 框架化分析（人群分层/触点效率/决策路径/建议）

分析策略：
1. 优先使用 LLM 做主题归纳和洞察提取
2. 无 API Key 时 fallback 到 jieba 分词 + TF-IDF + 规则引擎
"""

import re
import logging
from collections import Counter, defaultdict
from typing import Optional

import jieba
import jieba.analyse

from ..llm import chat_completion, extract_json

logger = logging.getLogger(__name__)

# 停用词
STOP_WORDS = set("的了是在我有和就不也这都人会对说要那去能到让被把给着没很好想用从过还上来下".split())


def analyze(comments: list[dict], research_goal: dict) -> dict:
    """
    对评论数据进行框架化分析。

    优先尝试 LLM 分析，失败时 fallback 到规则引擎。

    Args:
        comments: 标准化评论列表
        research_goal: 结构化研究目标

    Returns:
        包含 persona/pain_points/decision_path/recommendations/insights 的分析结果
    """
    keywords = research_goal.get("keywords", [])

    # 尝试 LLM 分析
    llm_result = _llm_analyze(comments, research_goal)
    if llm_result:
        logger.info("使用 LLM 分析结果")
        return llm_result

    # Fallback: NLP + 规则引擎
    logger.info("Fallback 到 NLP + 规则引擎分析")

    persona = _extract_persona(comments)
    pain_points = _extract_pain_points_nlp(comments, keywords)
    decision_path = _extract_decision_path(comments)
    recommendations = _generate_recommendations(pain_points, decision_path)

    # 构建洞察列表
    insights = []
    for i, pp in enumerate(pain_points):
        insights.append({
            "id": f"insight_{i+1:03d}",
            "type": "pain_point",
            "content": pp["content"],
            "source_ids": pp["source_ids"],
            "confidence": pp["confidence"],
        })

    return {
        "persona": persona,
        "pain_points": pain_points,
        "decision_path": decision_path,
        "recommendations": recommendations,
        "insights": insights,
    }


# ============================================================
# LLM 分析路径
# ============================================================

def _llm_analyze(comments: list[dict], research_goal: dict) -> Optional[dict]:
    """使用 LLM 做完整分析"""
    # 构建评论摘要（取前30条避免超长）
    comment_texts = []
    for c in comments[:30]:
        sentiment_tag = f"[{c.get('sentiment', '?')}]" if c.get("sentiment") else ""
        comment_texts.append(f"- {sentiment_tag} {c['text']} (来源:{c.get('source','?')})")

    comments_str = "\n".join(comment_texts)

    system_prompt = """你是一名资深市场研究分析师，擅长从消费者原声中提取结构化洞察。
请严格按照 JSON 格式输出，不要添加额外解释。"""

    user_prompt = f"""请分析以下{len(comments)}条消费者评论（展示前30条），研究目标是"{research_goal.get('title', '')}"。

评论数据：
{comments_str}

请输出 JSON，格式如下：
```json
{{
  "pain_points": [
    {{
      "content": "痛点描述",
      "evidence_count": 3,
      "keywords": ["相关关键词"],
      "severity": "high/medium/low"
    }}
  ],
  "decision_path": ["阶段1(触点)", "阶段2(触点)", ...],
  "persona_segments": [
    {{
      "name": "人群名称",
      "characteristics": "特征描述",
      "proportion_estimate": "占比估计"
    }}
  ],
  "recommendations": ["建议1", "建议2", ...]
}}
```

要求：
1. 痛点至少提取3-5个，必须有原声支撑
2. 决策路径要体现消费者从认知到购买的完整旅程
3. 人群分层基于评论中体现的不同决策风格
4. 建议要具体可执行"""

    response = chat_completion(user_prompt, system=system_prompt)
    if not response:
        return None

    data = extract_json(response)
    if not data:
        logger.warning("LLM 返回格式无法解析")
        return None

    # 将 LLM 结果转换为标准输出格式，绑定 source_ids
    return _convert_llm_result(data, comments)


def _convert_llm_result(data: dict, comments: list[dict]) -> dict:
    """将 LLM 输出转换为标准格式，并绑定 source_ids"""
    pain_points = []
    insights = []

    for i, pp in enumerate(data.get("pain_points", [])):
        content = pp.get("content", "")
        kws = pp.get("keywords", [])

        # 根据关键词回溯绑定 source_ids
        source_ids = []
        for c in comments:
            text = c.get("text", "")
            if any(kw in text for kw in kws) or _text_similarity(content, text) > 0.3:
                source_ids.append(c["id"])

        # 根据证据量计算置信度
        evidence = len(source_ids)
        if evidence >= 5:
            confidence = 0.9
        elif evidence >= 3:
            confidence = 0.75
        elif evidence >= 2:
            confidence = 0.6
        else:
            confidence = 0.4

        pain_points.append({
            "content": content,
            "source_ids": source_ids,
            "count": evidence,
            "confidence": confidence,
        })

        insights.append({
            "id": f"insight_{i+1:03d}",
            "type": "pain_point",
            "content": content,
            "source_ids": source_ids,
            "confidence": confidence,
        })

    # persona
    segments = data.get("persona_segments", [])
    persona = {
        "sample_size": len(comments),
        "segments": segments,
        "sentiment_distribution": dict(Counter(
            c.get("sentiment") for c in comments if c.get("sentiment")
        )),
    }

    return {
        "persona": persona,
        "pain_points": pain_points,
        "decision_path": data.get("decision_path", []),
        "recommendations": data.get("recommendations", []),
        "insights": insights,
    }


def _text_similarity(a: str, b: str) -> float:
    """简易文本相似度（基于字符重合度）"""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    intersection = set_a & set_b
    return len(intersection) / max(len(set_a), len(set_b))


# ============================================================
# NLP + 规则引擎 fallback
# ============================================================

def _extract_persona(comments: list[dict]) -> dict:
    """基于评论内容提取用户画像特征"""
    total = len(comments)
    sentiments = Counter(c.get("sentiment") for c in comments if c.get("sentiment"))
    sources = Counter(c.get("source") for c in comments)

    # 用 jieba 提取高频名词作为关注点
    all_text = " ".join(c.get("text", "") for c in comments)
    top_keywords = jieba.analyse.extract_tags(all_text, topK=15, withWeight=True)

    return {
        "sample_size": total,
        "sentiment_distribution": dict(sentiments),
        "source_distribution": dict(sources),
        "top_concerns": [{"keyword": kw, "weight": round(w, 3)} for kw, w in top_keywords],
    }


def _extract_pain_points_nlp(comments: list[dict], keywords: list[str]) -> list[dict]:
    """
    NLP 增强的痛点提取：
    1. 筛选负面评论
    2. jieba 分词 + TF-IDF 提取负面评论的核心主题
    3. 按主题聚类，绑定 source_ids
    """
    # 筛选负面评论
    negative_comments = []
    for c in comments:
        if c.get("sentiment") == "negative":
            negative_comments.append(c)
        elif _is_negative_by_rule(c.get("text", "")):
            negative_comments.append(c)

    if not negative_comments:
        return []

    # TF-IDF 提取负面评论的关键主题词
    neg_texts = [c.get("text", "") for c in negative_comments]
    combined_neg_text = " ".join(neg_texts)
    topic_keywords = jieba.analyse.extract_tags(combined_neg_text, topK=10, withWeight=True)

    # 按主题词聚类负面评论
    topic_groups = defaultdict(list)
    for c in negative_comments:
        text = c.get("text", "")
        words = set(jieba.cut(text))

        # 找到最相关的主题词
        best_topic = None
        best_score = 0
        for kw, weight in topic_keywords:
            if kw in STOP_WORDS or len(kw) < 2:
                continue
            if kw in text:
                if weight > best_score:
                    best_score = weight
                    best_topic = kw

        if best_topic:
            topic_groups[best_topic].append(c["id"])
        else:
            topic_groups["其他"].append(c["id"])

    # 生成痛点洞察
    pain_points = []
    for topic, source_ids in sorted(topic_groups.items(), key=lambda x: -len(x[1])):
        if topic == "其他" and len(source_ids) < 3:
            continue

        # 找到该主题下的代表性原声
        representative = ""
        for c in negative_comments:
            if c["id"] in source_ids:
                representative = c.get("text", "")[:50]
                break

        # 置信度计算
        count = len(source_ids)
        if count >= 5:
            confidence = 0.9
        elif count >= 3:
            confidence = 0.75
        elif count >= 2:
            confidence = 0.6
        else:
            confidence = 0.4

        pain_points.append({
            "content": "「%s」相关负面反馈（%d条），如：\"%s...\"" % (topic, count, representative),
            "topic": topic,
            "source_ids": source_ids,
            "count": count,
            "confidence": round(confidence, 2),
        })

    pain_points.sort(key=lambda x: x["count"], reverse=True)
    return pain_points


def _is_negative_by_rule(text: str) -> bool:
    """规则判断是否为负面"""
    patterns = [
        r"不好|太贵|贵了|过敏|不适|失望|差评|踩雷|鸡肋|割韭菜",
        r"不够|难|不爱|不知道|担心|纠结|假|软广|刷的",
    ]
    return any(re.search(p, text) for p in patterns)


def _extract_decision_path(comments: list[dict]) -> list[dict]:
    """提取消费者决策路径（对齐 Aware → Interest → Decide → Purchase 框架）"""
    stages = {
        "认知(Aware)": {
            "keywords": ["广告", "梯媒", "信息流", "推荐", "听说", "看到", "种草"],
            "sources": [],
        },
        "兴趣(Interest)": {
            "keywords": ["搜", "测评", "横测", "对比", "功课", "研究", "知乎"],
            "sources": [],
        },
        "决策(Decide)": {
            "keywords": ["选", "对比", "纠结", "最后", "决定", "排雷", "评论"],
            "sources": [],
        },
        "购买(Purchase)": {
            "keywords": ["买", "下单", "入手", "回购", "囤", "活动", "直播间"],
            "sources": [],
        },
        "分享(Share)": {
            "keywords": ["推荐给", "安利", "分享", "同事", "闺蜜", "朋友"],
            "sources": [],
        },
    }

    for c in comments:
        text = c.get("text", "")
        for stage_name, stage_info in stages.items():
            if any(kw in text for kw in stage_info["keywords"]):
                stage_info["sources"].append(c["id"])

    path = []
    for stage_name, stage_info in stages.items():
        count = len(stage_info["sources"])
        if count > 0:
            path.append({
                "stage": stage_name,
                "mention_count": count,
                "coverage": round(count / len(comments), 2),
            })

    return path


def _generate_recommendations(pain_points: list[dict], decision_path: list[dict]) -> list[str]:
    """基于痛点和决策路径生成建议"""
    recommendations = []

    # 基于痛点
    for pp in pain_points[:3]:
        topic = pp.get("topic", "")
        count = pp.get("count", 0)
        if count >= 3:
            recommendations.append(
                f"高优先级：「{topic}」问题反馈集中（{count}条），建议重点优化相关体验并加强正面内容布局"
            )
        else:
            recommendations.append(
                f"关注项：「{topic}」存在负面声音（{count}条），建议持续监控"
            )

    # 基于决策路径缺口
    if decision_path:
        weakest = min(decision_path, key=lambda x: x["coverage"])
        if weakest["coverage"] < 0.1:
            recommendations.append(
                f"路径缺口：「{weakest['stage']}」环节触点覆盖率仅{weakest['coverage']:.0%}，建议加强该阶段的内容/广告布局"
            )

    if not recommendations:
        recommendations.append("当前数据未发现显著痛点，建议扩大样本量后复验")

    return recommendations
