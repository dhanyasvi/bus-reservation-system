from openai import OpenAI
import openai
import config

def get_client() -> OpenAI:
    return OpenAI(
        api_key=config.LLM_API_KEY or "missing",
        base_url=config.LLM_BASE_URL or "https://api.openai.com/v1",
        timeout=15
    )

def ping() -> str:
    c = get_client()
    r = c.chat.completions.create(
        model=config.LLM_MODEL,
        max_tokens=5,
        messages=[{"role": "user", "content": "Reply with the word OK"}]
    )
    return r.choices[0].message.content or "OK"

def check_llm_status() -> dict:
    if not config.LLM_API_KEY or not config.LLM_API_KEY.strip():
        return {
            "available": False,
            "status": "unconfigured",
            "message": "No API key configured. Built-in Resilient Agent is active.",
            "provider": "Built-in Resilient Agent"
        }
    try:
        reply = ping()
        return {
            "available": True,
            "status": "ok",
            "message": f"LLM is online and responsive: {reply.strip()}",
            "provider": config.LLM_MODEL
        }
    except openai.RateLimitError as e:
        return {
            "available": False,
            "status": "rate_limited",
            "message": "LLM API credits exhausted or rate limit reached. Built-in Resilient Agent is handling requests.",
            "error_detail": str(e),
            "provider": "Built-in Resilient Agent"
        }
    except openai.AuthenticationError as e:
        return {
            "available": False,
            "status": "auth_error",
            "message": "Invalid API key. Built-in Resilient Agent is handling requests.",
            "error_detail": str(e),
            "provider": "Built-in Resilient Agent"
        }
    except Exception as e:
        return {
            "available": False,
            "status": "error",
            "message": f"Cannot reach LLM ({type(e).__name__}). Built-in Resilient Agent is handling requests.",
            "error_detail": str(e),
            "provider": "Built-in Resilient Agent"
        }

