import os
import litellm
from dotenv import load_dotenv

load_dotenv()

STREAMLAKE_API_KEY = os.environ["STREAMLAKE_API_KEY"]
STREAMLAKE_API_BASE = "https://vanchin.streamlake.ai/api/gateway/v1/endpoints"


def complete(model: str, messages: list[dict]) -> str:
    response = litellm.completion(
        model=f"openai/{model}",
        messages=messages,
        api_base=STREAMLAKE_API_BASE,
        api_key=STREAMLAKE_API_KEY,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    model = "ep-a23s52-1774502943903035372"
    messages = [{"role": "user", "content": "sfd"}]
    print(complete(model, messages))
