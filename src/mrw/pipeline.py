"""Pipeline 编排 — 串联所有 stage"""

import logging
import os
from dotenv import load_dotenv

from .stages import parse_brief, collect_data, analyze, validate, generate_report

# 加载 .env
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(brief_path: str, data_path: str, output_dir: str) -> dict:
    """
    运行完整研究工作流。

    Args:
        brief_path: Brief YAML 路径
        data_path: 数据文件路径
        output_dir: 输出目录

    Returns:
        Pipeline 运行结果摘要
    """
    logger.info("=" * 50)
    logger.info("AI 辅助市场研究工作流 启动")
    logger.info("=" * 50)

    # 检查 LLM 可用性
    has_llm = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    logger.info(f"LLM 模式: {'已启用' if has_llm else '规则引擎 (未配置 API Key)'}")

    # Stage 1: 解析 Brief
    research_goal = parse_brief(brief_path)
    print(f"[1/5] Brief 解析完成：{research_goal['title']}")
    logger.info(f"品类: {research_goal.get('category', 'N/A')}")
    logger.info(f"研究维度: {research_goal.get('dimensions', [])}")

    # Stage 2: 数据采集
    comments = collect_data(data_path, keywords=research_goal.get("keywords"))
    print(f"[2/5] 数据加载完成：{len(comments)} 条")

    # Stage 3: 框架分析
    analysis = analyze(comments, research_goal)
    print(f"[3/5] 框架分析完成：{len(analysis['insights'])} 条洞察")
    logger.info(f"决策路径: {[s.get('stage', s) if isinstance(s, dict) else s for s in analysis.get('decision_path', [])]}")

    # Stage 4: 三元校验
    validation = validate(analysis["insights"], comments)
    summary = validation["summary"]
    print(f"[4/5] 三元校验完成：通过率 {summary['pass_rate']:.0%}（高{summary['high']}/中{summary['medium']}/低{summary['low']}）")

    # Stage 5: 报告生成
    report_path = generate_report(research_goal, analysis, validation, output_dir)
    print(f"[5/5] 报告生成完成：{report_path}")

    logger.info("=" * 50)
    logger.info("Pipeline 完成")
    logger.info("=" * 50)

    return {
        "research_goal": research_goal,
        "sample_size": len(comments),
        "insights_count": len(analysis["insights"]),
        "validation_summary": validation["summary"],
        "report_path": report_path,
    }
