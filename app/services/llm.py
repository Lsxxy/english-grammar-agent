from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        if not self.settings.active_llm_api_key:
            return None
        provider = self.settings.llm_provider.lower().strip()
        if provider == "openai" and not self.settings.llm_base_url:
            return await self._openai_responses(messages)
        return await self._openai_compatible_chat(messages)

    async def _openai_responses(self, messages: list[dict[str, str]]) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.active_llm_api_key)
        response = await client.responses.create(
            model=self.settings.active_llm_model,
            input=messages,
        )
        return response.output_text.strip()

    async def _openai_compatible_chat(self, messages: list[dict[str, str]]) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.settings.active_llm_api_key,
            base_url=self.settings.llm_base_url,
        )
        response = await client.chat.completions.create(
            model=self.settings.active_llm_model,
            messages=messages,
        )
        content = response.choices[0].message.content
        return (content or "").strip()
