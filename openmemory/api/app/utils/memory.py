"""
Memory client utilities for OpenMemory.

This module provides functionality to initialize and manage the Mem0 memory client
with automatic configuration management and Docker environment support.

Docker Ollama Configuration:
When running inside a Docker container and using Ollama as the LLM or embedder provider,
the system automatically detects the Docker environment and adjusts localhost URLs
to properly reach the host machine where Ollama is running.

Supported Docker host resolution (in order of preference):
1. OLLAMA_HOST environment variable (if set)
2. host.docker.internal (Docker Desktop for Mac/Windows)
3. Docker bridge gateway IP (typically 172.17.0.1 on Linux)
4. Fallback to 172.17.0.1

Example configuration that will be automatically adjusted:
{
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:latest",
            "ollama_base_url": "http://localhost:11434"  # Auto-adjusted in Docker
        }
    }
}
"""

import copy
import hashlib
import json
import os
import socket

from app.database import SessionLocal
from app.models import Config as ConfigModel
from app.utils.providers import get_provider
from app.utils.vector_stores import detect_vector_store

from mem0 import Memory

_memory_client = None
_config_hash = None


def _get_config_hash(config_dict):
    """Generate a hash of the config to detect changes."""
    config_str = json.dumps(config_dict, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()


def _get_docker_host_url():
    """
    Determine the appropriate host URL to reach host machine from inside Docker container.
    Returns the best available option for reaching the host from inside a container.
    """
    # Check for custom environment variable first
    custom_host = os.environ.get('OLLAMA_HOST')
    if custom_host:
        print(f"Using custom Ollama host from OLLAMA_HOST: {custom_host}")
        return custom_host.replace('http://', '').replace('https://', '').split(':')[0]
    
    # Check if we're running inside Docker
    if not os.path.exists('/.dockerenv'):
        # Not in Docker, return localhost as-is
        return "localhost"
    
    print("Detected Docker environment, adjusting host URL for Ollama...")
    
    # Try different host resolution strategies
    host_candidates = []
    
    # 1. host.docker.internal (works on Docker Desktop for Mac/Windows)
    try:
        socket.gethostbyname('host.docker.internal')
        host_candidates.append('host.docker.internal')
        print("Found host.docker.internal")
    except socket.gaierror:
        pass
    
    # 2. Docker bridge gateway (typically 172.17.0.1 on Linux)
    try:
        with open('/proc/net/route', 'r') as f:
            for line in f:
                fields = line.strip().split()
                if fields[1] == '00000000':  # Default route
                    gateway_hex = fields[2]
                    gateway_ip = socket.inet_ntoa(bytes.fromhex(gateway_hex)[::-1])
                    host_candidates.append(gateway_ip)
                    print(f"Found Docker gateway: {gateway_ip}")
                    break
    except (FileNotFoundError, IndexError, ValueError):
        pass
    
    # 3. Fallback to common Docker bridge IP
    if not host_candidates:
        host_candidates.append('172.17.0.1')
        print("Using fallback Docker bridge IP: 172.17.0.1")
    
    # Return the first available candidate
    return host_candidates[0]


def _fix_ollama_urls(config_section):
    """
    Fix Ollama URLs for Docker environment.
    Replaces localhost URLs with appropriate Docker host URLs.
    Sets default ollama_base_url if not provided.
    """
    if not config_section or "config" not in config_section:
        return config_section
    
    ollama_config = config_section["config"]
    
    # Set default ollama_base_url if not provided
    if "ollama_base_url" not in ollama_config:
        ollama_config["ollama_base_url"] = "http://host.docker.internal:11434"
    else:
        # Check for ollama_base_url and fix if it's localhost
        url = ollama_config["ollama_base_url"]
        if "localhost" in url or "127.0.0.1" in url:
            docker_host = _get_docker_host_url()
            if docker_host != "localhost":
                new_url = url.replace("localhost", docker_host).replace("127.0.0.1", docker_host)
                ollama_config["ollama_base_url"] = new_url
                print(f"Adjusted Ollama URL from {url} to {new_url}")
    
    return config_section


def reset_memory_client():
    """Reset the global memory client to force reinitialization with new config."""
    global _memory_client, _config_hash
    _memory_client = None
    _config_hash = None


# --- LLM provider config factories ---

def _build_ollama_llm_config(model, api_key, base_url, ollama_base_url):
    config = {"model": model or "llama3.1:latest"}
    # OLLAMA_BASE_URL takes precedence, then LLM_BASE_URL, then default
    config["ollama_base_url"] = ollama_base_url or base_url or "http://localhost:11434"
    return config


def _build_openai_llm_config(model, api_key, base_url, ollama_base_url):
    config = {
        "model": model or "gpt-4o-mini",
        "api_key": api_key or "env:OPENAI_API_KEY",
    }
    if base_url:
        config["openai_base_url"] = base_url
    return config


_LLM_CONFIG_FACTORIES = {
    "ollama": _build_ollama_llm_config,
    "openai": _build_openai_llm_config,
}


def _create_llm_config(provider, model, api_key, base_url, ollama_base_url):
    """
    Build LLM config dict for mem0.

    `provider` here is already the mem0-native provider name (after registry
    translation), e.g. "openai" even when the user chose "qwen".
    """
    base_config = {
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    factory = _LLM_CONFIG_FACTORIES.get(provider)
    if factory:
        base_config.update(factory(model, api_key, base_url, ollama_base_url))
    else:
        # Generic provider (anthropic, groq, together, deepseek, etc.)
        if not model:
            raise ValueError(
                f"LLM_MODEL environment variable is required when using LLM_PROVIDER='{provider}'. "
                f"Set LLM_MODEL to a valid model name for the '{provider}' provider."
            )
        base_config["model"] = model
        if api_key:
            base_config["api_key"] = api_key

    return base_config


# --- Embedder provider config factories ---

def _build_ollama_embedder_config(model, api_key, base_url, ollama_base_url, llm_base_url):
    config = {"model": model or "nomic-embed-text"}
    config["ollama_base_url"] = base_url or ollama_base_url or llm_base_url or "http://localhost:11434"
    return config


def _build_openai_embedder_config(model, api_key, base_url, ollama_base_url, llm_base_url):
    config = {
        "model": model or "text-embedding-3-small",
        "api_key": api_key or "env:OPENAI_API_KEY",
    }
    if base_url:
        config["openai_base_url"] = base_url
    return config


_EMBEDDER_CONFIG_FACTORIES = {
    "ollama": _build_ollama_embedder_config,
    "openai": _build_openai_embedder_config,
}


def _create_embedder_config(provider, model, api_key, base_url, ollama_base_url, llm_base_url):
    """Build embedder config using registered provider factory or generic fallback."""
    factory = _EMBEDDER_CONFIG_FACTORIES.get(provider)
    if factory:
        config = factory(model, api_key, base_url, ollama_base_url, llm_base_url)
    else:
        if not model:
            raise ValueError(
                f"EMBEDDER_MODEL environment variable is required when using EMBEDDER_PROVIDER='{provider}'. "
                f"Set EMBEDDER_MODEL to a valid model name for the '{provider}' provider."
            )
        config = {"model": model}
        if api_key:
            config["api_key"] = api_key

    return config


def get_default_memory_config():
    """Get default memory client configuration with sensible defaults."""
    # ── Vector store: strategy pattern, auto-detected from env vars ──────────
    vs_strategy = detect_vector_store()
    vs_section = vs_strategy.get_mem0_config()
    print(f"Auto-detected vector store: {vs_strategy.provider_name} "
          f"with config: {vs_section['config']}")


    # Detect LLM provider from environment variables, with registry-based resolution
    llm_provider_alias = os.environ.get('LLM_PROVIDER', 'openai').lower()
    llm_provider_def = get_provider(llm_provider_alias)
    # mem0_llm_provider is the name mem0 understands (e.g. "openai" for both openai and qwen)
    mem0_llm_provider = llm_provider_def.mem0_provider if llm_provider_def else llm_provider_alias

    llm_model = (
        os.environ.get('LLM_MODEL')
        or (llm_provider_def.default_llm_model if llm_provider_def else None)
    )
    # LLM_API_KEY overrides; fall back to provider-specific env var from registry
    llm_api_key = (
        os.environ.get('LLM_API_KEY')
        or (os.environ.get(llm_provider_def.api_key_env) if llm_provider_def and llm_provider_def.api_key_env else None)
    )
    # LLM_BASE_URL overrides; fall back to provider default from registry
    llm_base_url = (
        os.environ.get('LLM_BASE_URL')
        or (llm_provider_def.base_url if llm_provider_def else None)
    )
    ollama_base_url = os.environ.get('OLLAMA_BASE_URL')

    llm_config = _create_llm_config(
        provider=mem0_llm_provider,
        model=llm_model,
        api_key=llm_api_key,
        base_url=llm_base_url,
        ollama_base_url=ollama_base_url,
    )
    print(f"Auto-detected LLM provider: {llm_provider_alias} (mem0: {mem0_llm_provider})")

    # Detect embedder provider — default follows LLM provider (same vendor is most compatible)
    embedder_provider_alias = os.environ.get('EMBEDDER_PROVIDER', llm_provider_alias).lower()
    embedder_provider_def = get_provider(embedder_provider_alias)
    mem0_embedder_provider = embedder_provider_def.mem0_provider if embedder_provider_def else embedder_provider_alias

    embedder_model = (
        os.environ.get('EMBEDDER_MODEL')
        or (embedder_provider_def.default_embedder_model if embedder_provider_def else None)
    )
    embedder_api_key = (
        os.environ.get('EMBEDDER_API_KEY')
        or (os.environ.get(embedder_provider_def.api_key_env) if embedder_provider_def and embedder_provider_def.api_key_env else None)
    )
    embedder_base_url = (
        os.environ.get('EMBEDDER_BASE_URL')
        or (embedder_provider_def.base_url if embedder_provider_def else None)
    )

    embedder_config = _create_embedder_config(
        provider=mem0_embedder_provider,
        model=embedder_model,
        api_key=embedder_api_key,
        base_url=embedder_base_url,
        ollama_base_url=ollama_base_url,
        llm_base_url=llm_base_url,
    )
    print(f"Auto-detected embedder provider: {embedder_provider_alias} (mem0: {mem0_embedder_provider})")

    return {
        "vector_store": vs_section,
        "llm": {
            "provider": mem0_llm_provider,
            "config": llm_config
        },
        "embedder": {
            "provider": mem0_embedder_provider,
            "config": embedder_config
        },
        "version": "v1.1"
    }


def _normalize_provider_section(section: dict) -> dict:
    """
    Translate a user-facing provider alias in a config section to what mem0 expects.

    For example, when a user stores {"provider": "qwen", "config": {...}} in the DB,
    this function rewrites it to {"provider": "openai", "config": {..., "openai_base_url": ..., "api_key": ...}}
    so that mem0 can process it with its native OpenAI driver.

    Sections whose provider is already a native mem0 name pass through unchanged.
    """
    if not section or "provider" not in section:
        return section

    alias = section["provider"].lower()
    provider_def = get_provider(alias)

    if provider_def is None:
        return section  # Unknown provider — leave as-is and let mem0 handle/error

    if provider_def.mem0_provider == alias:
        return section  # Already a native mem0 provider name; no translation needed

    section = copy.deepcopy(section)
    section["provider"] = provider_def.mem0_provider
    cfg = section.setdefault("config", {})

    # Inject base_url (e.g. Qwen's DashScope endpoint) if not already present
    if provider_def.base_url and "openai_base_url" not in cfg:
        cfg["openai_base_url"] = provider_def.base_url

    # Inject api_key from the provider-specific env var if not already set
    if provider_def.api_key_env and "api_key" not in cfg:
        cfg["api_key"] = f"env:{provider_def.api_key_env}"

    return section


def _parse_environment_variables(config_dict):
    """
    Parse environment variables in config values.
    Converts 'env:VARIABLE_NAME' to actual environment variable values.
    """
    if isinstance(config_dict, dict):
        parsed_config = {}
        for key, value in config_dict.items():
            if isinstance(value, str) and value.startswith("env:"):
                env_var = value.split(":", 1)[1]
                env_value = os.environ.get(env_var)
                if env_value:
                    parsed_config[key] = env_value
                    print(f"Loaded {env_var} from environment for {key}")
                else:
                    print(f"Warning: Environment variable {env_var} not found, keeping original value")
                    parsed_config[key] = value
            elif isinstance(value, dict):
                parsed_config[key] = _parse_environment_variables(value)
            else:
                parsed_config[key] = value
        return parsed_config
    return config_dict


def get_memory_client(custom_instructions: str = None):
    """
    Get or initialize the Mem0 client.

    Args:
        custom_instructions: Optional instructions for the memory project.

    Returns:
        Initialized Mem0 client instance or None if initialization fails.

    Raises:
        Exception: If required API keys are not set or critical configuration is missing.
    """
    global _memory_client, _config_hash

    try:
        # Start with default configuration
        config = get_default_memory_config()
        
        # Variable to track custom instructions
        db_custom_instructions = None
        
        # Load configuration from database
        try:
            db = SessionLocal()
            db_config = db.query(ConfigModel).filter(ConfigModel.key == "main").first()
            
            if db_config:
                json_config = db_config.value
                
                # Extract custom instructions from openmemory settings
                if "openmemory" in json_config and "custom_instructions" in json_config["openmemory"]:
                    db_custom_instructions = json_config["openmemory"]["custom_instructions"]
                
                # Override defaults with configurations from the database
                if "mem0" in json_config:
                    mem0_config = json_config["mem0"]
                    
                    # Update LLM configuration if available
                    if "llm" in mem0_config and mem0_config["llm"] is not None:
                        config["llm"] = _normalize_provider_section(mem0_config["llm"])

                    # Update Embedder configuration if available
                    if "embedder" in mem0_config and mem0_config["embedder"] is not None:
                        config["embedder"] = _normalize_provider_section(mem0_config["embedder"])

                    if "vector_store" in mem0_config and mem0_config["vector_store"] is not None:
                        config["vector_store"] = mem0_config["vector_store"]
            else:
                print("No configuration found in database, using defaults")
                    
            db.close()
                            
        except Exception as e:
            print(f"Warning: Error loading configuration from database: {e}")
            print("Using default configuration")
            # Continue with default configuration if database config can't be loaded

        # Use custom_instructions parameter first, then fall back to database value
        instructions_to_use = custom_instructions or db_custom_instructions
        if instructions_to_use:
            config["custom_fact_extraction_prompt"] = instructions_to_use

        # Fix Ollama URLs for Docker environment (applies to both env-var defaults and DB overrides)
        if config.get("llm", {}).get("provider") == "ollama":
            config["llm"] = _fix_ollama_urls(config["llm"])
        if config.get("embedder", {}).get("provider") == "ollama":
            config["embedder"] = _fix_ollama_urls(config["embedder"])

        # ALWAYS parse environment variables in the final config
        # This ensures that even default config values like "env:OPENAI_API_KEY" get parsed
        print("Parsing environment variables in final config...")
        config = _parse_environment_variables(config)

        # Check if config has changed by comparing hashes
        current_config_hash = _get_config_hash(config)
        
        # Only reinitialize if config changed or client doesn't exist
        if _memory_client is None or _config_hash != current_config_hash:
            print(f"Initializing memory client with config hash: {current_config_hash}")
            try:
                _memory_client = Memory.from_config(config_dict=config)
                _config_hash = current_config_hash
                print("Memory client initialized successfully")
            except Exception as init_error:
                print(f"Warning: Failed to initialize memory client: {init_error}")
                print("Server will continue running with limited memory functionality")
                _memory_client = None
                _config_hash = None
                return None
        
        return _memory_client
        
    except Exception as e:
        print(f"Warning: Exception occurred while initializing memory client: {e}")
        print("Server will continue running with limited memory functionality")
        return None


def get_default_user_id():
    return "default_user"
