import os
from dotenv import load_dotenv

load_dotenv()


def get_openai_api_key():
    return os.getenv("OPENAI_API_KEY", "")


def set_openai_api_key(key):
    os.environ["OPENAI_API_KEY"] = key


def get_openai_api_model():
    return os.getenv("OPENAI_API_MODEL", "")


def set_openai_api_model(model):
    os.environ["OPENAI_API_MODEL"] = model


def get_openai_api_models():
    return os.getenv("OPENAI_API_MODELS").split(",")


def get_base_system_prompt():
    return os.getenv("BASE_SYSTEM_PROMPT", "")
