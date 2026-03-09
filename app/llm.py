import os
from typing import Any, Dict, List, Tuple

import httpx
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

class LLMError(Exception):
    pass

def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()

def _openai_cfg() -> Tuple[str, str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY environment variable is not set.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return api_key, base_url.rstrip("/") + "/", model

def _nebius_cfg() -> Tuple[str, str, str]:
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        raise LLMError("NEBIUS_API_KEY environment variable is not set.")
    base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
    model = os.getenv("NEBIUS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct-fast")
    return api_key, base_url.rstrip("/") + "/", model

def _get_langchain_llm(json_mode: bool = False) -> ChatOpenAI:
    provider = _provider()
    if provider == "openai":
        api_key, base_url, model = _openai_cfg()
    elif provider == "nebius":
        api_key, base_url, model = _nebius_cfg()
    else:
        raise LLMError('LLM_PROVIDER must be "openai" or "nebius".')

    model_kwargs = {}
    if json_mode and provider == "openai":
        model_kwargs["response_format"] = {"type": "json_object"}

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.2,
        max_retries=3,
        model_kwargs=model_kwargs,
    )

async def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.2, json_mode: bool = False) -> str:
    llm = _get_langchain_llm(json_mode=json_mode)
    llm.temperature = temperature

    # Convert messages to LangChain format
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))

    # Use invoke for synchronous call, but since we're in async context, we can use it
    response = await llm.ainvoke(langchain_messages)
    return response.content
