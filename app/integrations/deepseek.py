from openai import OpenAI
from app.config import get_settings
from app.utils.logger import logger


class DeepSeekClient:
    def __init__(self, model: str):
        settings = get_settings()
        self._api_key = settings.deepseek_api_key
        self._model = model

    @property
    def _client(self) -> OpenAI:
        return OpenAI(api_key=self._api_key, base_url="https://api.deepseek.com")

    async def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        if not self._api_key:
            logger.warning("DeepSeek API key not configured, returning fallback response")
            return ""

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            return ""
