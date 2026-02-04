from openai import AsyncOpenAI


class OpenAI:
    def __init__(
        self,
        model: str = "llama-3.1-8b-instruct",
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        max_tokens: int = 20,
        temperature: float = 0.7,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        self.base_prompt = """You are a word-combining system.
        Input: two words or concepts.
        Task: produce exactly ONE combined result that merges both inputs.
        Output rules: 
        - Output ONLY the combined result 
        - One word or short phrase 
        - Add ONLY ONE relevant emoji at the start
        - No explanation 
        - No extra text 
        - If the result cannot be generated return: ❌ Failed
        - Stop after the result. 
        Example: Fire + Water → 💨Steam"""

    async def generate(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.base_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content
