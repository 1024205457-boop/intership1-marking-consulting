"""LLM 调用层 — 统一封装 OpenAI/Anthropic，无 API Key 时 fallback 到规则引擎"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_client():
    """获取可用的 LLM client，无 key 则返回 None"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except ImportError:
            logger.warning("openai 包未安装，fallback 到规则引擎")
            return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=api_key)
        except ImportError:
            logger.warning("anthropic 包未安装，fallback 到规则引擎")
            return None

    return None


def chat_completion(
    prompt: str,
    system: str = "",
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> Optional[str]:
    """
    调用 LLM 获取回复。

    Returns:
        回复文本，调用失败时返回 None（由调用方 fallback 到规则引擎）
    """
    client = get_client()
    if client is None:
        logger.info("未配置 API Key，跳过 LLM 调用")
        return None

    try:
        # OpenAI
        if hasattr(client, "chat"):
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system} if system else None,
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # filter None messages
            return resp.choices[0].message.content

        # Anthropic
        if hasattr(client, "messages"):
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return resp.content[0].text

    except Exception as e:
        logger.warning(f"LLM 调用失败: {e}，fallback 到规则引擎")
        return None

    return None


def extract_json(text: str) -> Optional[dict]:
    """从 LLM 回复中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown code block 中提取
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None
