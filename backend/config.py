import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@localhost/busdb")
CITIES = {"Bangalore", "Chennai", "Hyderabad", "Mumbai", "Pune", "Delhi", "Kolkata", "Mysore", "Goa"}
MAX_SEAT = 40

def get_masked_key() -> str:
    if not LLM_API_KEY:
        return "None (Using Built-in Resilient Agent)"
    if len(LLM_API_KEY) <= 8:
        return "****"
    return f"{LLM_API_KEY[:4]}...{LLM_API_KEY[-4:]}"

def get_config_dict() -> dict:
    return {
        "llm_api_key_masked": get_masked_key(),
        "has_api_key": bool(LLM_API_KEY and LLM_API_KEY.strip()),
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
        "has_admin_key": bool(ADMIN_API_KEY and ADMIN_API_KEY.strip()),
        "cities": sorted(list(CITIES)),
        "max_seats": MAX_SEAT,
    }

def update_llm_settings(api_key: str = None, base_url: str = None, model: str = None, persist_to_env: bool = True):
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    if api_key is not None:
        LLM_API_KEY = api_key.strip()
        os.environ["LLM_API_KEY"] = LLM_API_KEY
    if base_url is not None:
        LLM_BASE_URL = base_url.strip()
        os.environ["LLM_BASE_URL"] = LLM_BASE_URL
    if model is not None:
        LLM_MODEL = model.strip()
        os.environ["LLM_MODEL"] = LLM_MODEL

    if persist_to_env:
        try:
            lines = []
            if ENV_PATH.exists():
                with open(ENV_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            
            keys_updated = {"LLM_API_KEY": False, "LLM_BASE_URL": False, "LLM_MODEL": False}
            new_lines = []
            for line in lines:
                k = line.split("=", 1)[0].strip() if "=" in line else ""
                if k == "LLM_API_KEY":
                    new_lines.append(f"LLM_API_KEY={LLM_API_KEY}\n")
                    keys_updated["LLM_API_KEY"] = True
                elif k == "LLM_BASE_URL":
                    new_lines.append(f"LLM_BASE_URL={LLM_BASE_URL}\n")
                    keys_updated["LLM_BASE_URL"] = True
                elif k == "LLM_MODEL":
                    new_lines.append(f"LLM_MODEL={LLM_MODEL}\n")
                    keys_updated["LLM_MODEL"] = True
                else:
                    new_lines.append(line)
            
            for k, updated in keys_updated.items():
                if not updated:
                    val = LLM_API_KEY if k == "LLM_API_KEY" else (LLM_BASE_URL if k == "LLM_BASE_URL" else LLM_MODEL)
                    new_lines.append(f"{k}={val}\n")
                    
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Warning: could not write to .env: {e}")

