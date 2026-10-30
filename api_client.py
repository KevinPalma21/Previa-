import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def create_model_client() -> tuple[OpenAI, str]:
    """Prepare a client and model name. This does not make an API request."""
    load_dotenv(Path(__file__).parent / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    if not api_key:
        raise ValueError("Add OPENAI_API_KEY to your local .env file.")
    if not model:
        raise ValueError("Add OPENAI_MODEL to your local .env file.")

    client = OpenAI(api_key=api_key, timeout=30.0, max_retries=0)
    return client, model
