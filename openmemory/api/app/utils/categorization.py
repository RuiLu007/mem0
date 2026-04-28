import logging
import os
from typing import List

from app.utils.prompts import MEMORY_CATEGORIZATION_PROMPT
from app.utils.providers import make_openai_client
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# Simple keyword-based categories for mock mode (no API key required)
_MOCK_CATEGORY_RULES = {
    "房间": ["客房", "标准间", "大床房", "双床房", "套房", "房型"],
    "价格": ["多少钱", "费用", "报价", "优惠", "折扣", "房价", "元/晚"],
    "餐饮": ["早餐", "餐饮", "用餐", "自助餐", "逸厨"],
    "停车": ["停车", "泊车", "车位", "停车场"],
    "入住退房": ["入住", "退房", "check-in", "check-out", "押金"],
    "设施": ["健身", "游泳", "泳池", "spa", "会议室", "商务"],
    "预订": ["预订", "预定", "订房", "取消", "退款"],
    "位置": ["位置", "地址", "地铁", "交通", "打车"],
    "发票": ["发票", "收据", "报销", "税票"],
    "微信客服": ["微信", "wechat", "咨询", "客服"],
    "投诉反馈": ["投诉", "反馈", "表扬", "满意", "不满"],
}


def _mock_categorize(memory: str) -> List[str]:
    """Rule-based categorization without API key."""
    memory_lower = memory.lower()
    matched = []
    for category, keywords in _MOCK_CATEGORY_RULES.items():
        if any(kw in memory_lower for kw in keywords):
            matched.append(category)
    return matched if matched else ["general"]


def _is_mock_mode(provider_alias: str, api_key: str) -> bool:
    """Return True when real LLM calls should be skipped."""
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return True
    # Ollama doesn't use the structured-output parse endpoint
    if provider_alias == "ollama":
        return True
    if not api_key or api_key.startswith("sk-mock") or api_key == "no-key":
        return True
    return False


class MemoryCategories(BaseModel):
    categories: List[str]


def get_categories_for_memory(memory: str) -> List[str]:
    """
    Get categories for a memory.

    Uses the active LLM provider (from LLM_PROVIDER env) to call the
    structured-output parse endpoint. Falls back to keyword rules when:
    - MOCK_MODE=true
    - Provider is ollama (no parse endpoint)
    - No valid API key found
    - Any API call fails
    """
    provider_alias = os.getenv("LLM_PROVIDER", "openai").lower()

    # Resolve API key via provider registry (checks primary + alias env vars)
    from app.utils.providers import get_provider, resolve_api_key
    provider_def = get_provider(provider_alias)
    api_key = resolve_api_key(provider_alias)

    if _is_mock_mode(provider_alias, api_key):
        return _mock_categorize(memory)

    # Determine model for categorization
    model = os.getenv("LLM_MODEL") or (provider_def.default_llm_model if provider_def else "gpt-4o-mini")

    try:
        client = make_openai_client(provider_alias)
        messages = [
            {"role": "system", "content": MEMORY_CATEGORIZATION_PROMPT},
            {"role": "user", "content": memory}
        ]
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=MemoryCategories,
            temperature=0
        )
        parsed: MemoryCategories = completion.choices[0].message.parsed
        return [cat.strip().lower() for cat in parsed.categories]
    except Exception as e:
        logging.warning(f"[WARN] LLM categorization failed ({provider_alias}), using mock: {e}")
        return _mock_categorize(memory)
