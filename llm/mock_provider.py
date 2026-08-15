import asyncio
from typing import AsyncGenerator, List, Dict, Any
from .base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider generating simulated responses and streaming tokens.
    """

    QUESTIONS = [
        "Thank you for sharing that. Could you describe a challenging technical project you led recently, and how you evaluated the tradeoffs?",
        "That's very relevant. In this role, performance and reliability are paramount. How do you approach testing and monitoring in production?",
        "Interesting background. Can you share an example of a disagreement with a team member or stakeholder, and how you navigated it?",
        "Great answer. When dealing with unexpected incidents or technical debt, what structured debugging methodology do you follow?",
        "Thank you. To conclude our core discussion, what are you looking for most in your next team and engineering culture?"
    ]

    async def generate_response(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> str:
        await asyncio.sleep(0.4)
        user_msgs = [m for m in messages if m.get("role") == "user"]
        idx = min(len(user_msgs), len(self.QUESTIONS) - 1)
        return self.QUESTIONS[idx]

    async def generate_stream(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        full_text = await self.generate_response(system_prompt, messages, **kwargs)
        for word in full_text.split(" "):
            await asyncio.sleep(0.04)
            yield word + " "
