"""
Provider registry for multi-provider LLM and embedding support.

To add a new provider:
1. Add an entry to PROVIDER_REGISTRY with a ProviderDef.
2. If the provider uses an OpenAI-compatible API, set mem0_provider="openai" and provide base_url.
3. If the provider has native mem0 support, set mem0_provider to the native name.
4. Update api_key_env to the environment variable that holds the API key.
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ProviderDef:
    """Definition for an LLM/Embedder provider."""
    mem0_provider: str           # The provider name mem0 understands internally
    api_key_env: str             # Environment variable name for the API key (empty = no key needed)
    default_llm_model: str       # Default LLM model name
    default_embedder_model: str  # Default embedding model name
    base_url: Optional[str] = None  # API base URL override (for OpenAI-compatible endpoints)


# Registry maps user-facing provider alias → ProviderDef
# The alias is what users specify in LLM_PROVIDER env var or via the config API.
PROVIDER_REGISTRY: Dict[str, ProviderDef] = {
    "openai": ProviderDef(
        mem0_provider="openai",
        api_key_env="OPENAI_API_KEY",
        default_llm_model="gpt-4o-mini",
        default_embedder_model="text-embedding-3-small",
    ),
    "qwen": ProviderDef(
        mem0_provider="openai",          # Qwen uses the OpenAI-compatible API
        api_key_env="DASHSCOPE_API_KEY",
        default_llm_model="qwen-plus",
        default_embedder_model="text-embedding-v3",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "ollama": ProviderDef(
        mem0_provider="ollama",
        api_key_env="",                  # No API key required
        default_llm_model="llama3.1:latest",
        default_embedder_model="nomic-embed-text",
    ),
    # ── Add more providers below ──────────────────────────────────────────────
    # "azure_openai": ProviderDef(
    #     mem0_provider="azure_openai",
    #     api_key_env="AZURE_OPENAI_API_KEY",
    #     default_llm_model="gpt-4o",
    #     default_embedder_model="text-embedding-3-small",
    # ),
    # "anthropic": ProviderDef(
    #     mem0_provider="anthropic",
    #     api_key_env="ANTHROPIC_API_KEY",
    #     default_llm_model="claude-3-5-sonnet-20241022",
    #     default_embedder_model="",      # Anthropic has no embedding model; use openai for embedder
    # ),
    # "deepseek": ProviderDef(
    #     mem0_provider="openai",         # DeepSeek is OpenAI-compatible
    #     api_key_env="DEEPSEEK_API_KEY",
    #     default_llm_model="deepseek-chat",
    #     default_embedder_model="",
    #     base_url="https://api.deepseek.com/v1",
    # ),
}


def get_provider(name: str) -> Optional[ProviderDef]:
    """Get provider definition by alias name. Returns None if not registered."""
    return PROVIDER_REGISTRY.get(name.lower())


def list_providers() -> Dict[str, dict]:
    """Return all provider definitions as JSON-serialisable dicts."""
    return {
        name: {
            "mem0_provider": p.mem0_provider,
            "api_key_env": p.api_key_env,
            "default_llm_model": p.default_llm_model,
            "default_embedder_model": p.default_embedder_model,
            "base_url": p.base_url,
        }
        for name, p in PROVIDER_REGISTRY.items()
    }


def resolve_api_key(provider_name: str, override: Optional[str] = None) -> str:
    """
    Resolve API key for a provider.
    Priority: explicit override → provider-specific env var.
    """
    if override:
        return override
    provider = get_provider(provider_name)
    if provider and provider.api_key_env:
        return os.environ.get(provider.api_key_env, "")
    return ""


def make_openai_client(
    provider_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """
    Create an OpenAI SDK client for any OpenAI-compatible provider.

    Works for: openai, qwen, deepseek, or any provider whose mem0_provider is "openai".
    Looks up the registry to fill in base_url and api_key_env automatically.
    """
    from openai import OpenAI

    provider = get_provider(provider_name)
    effective_api_key = api_key or resolve_api_key(provider_name)
    effective_base_url = base_url or (provider.base_url if provider else None)

    kwargs: dict = {"api_key": effective_api_key or "no-key"}
    if effective_base_url:
        kwargs["base_url"] = effective_base_url

    return OpenAI(**kwargs)
