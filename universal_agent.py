"""Universal AI Agent - multi-provider with Gemini support."""
import logging
from typing import Optional, Dict, List
from datetime import datetime

from agent_config import AI_PROVIDERS, DEFAULT_AI_PROVIDER

logger = logging.getLogger(__name__)


class UniversalAIAgent:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or DEFAULT_AI_PROVIDER
        self.ai_client = self._init_provider()
        self.task_history: List[Dict] = []
        self.memory: Dict = {}
        logger.info(f"AI Agent ready — provider: {self.provider}")

    def _init_provider(self):
        cfg = AI_PROVIDERS.get(self.provider, {})
        if not cfg.get("enabled"):
            logger.warning(f"Provider {self.provider} not configured")
            return None
        try:
            if self.provider == "gemini":
                from google import genai
                return genai.Client(api_key=cfg["api_key"])
        except Exception as e:
            logger.error(f"Failed to init {self.provider}: {e}")
        return None

    async def process_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        try:
            system = self._build_system(context)
            if self.provider == "gemini":
                response = self._gemini(system, prompt)
            else:
                response = "AI provider not available"
            self._store(prompt, response)
            return response
        except Exception as e:
            logger.error(f"process_prompt error: {e}")
            return f"Error: {e}"

    def _build_system(self, context: Optional[Dict]) -> str:
        base = f"""You are Universal AI Agent — advanced assistant.
Date: {datetime.now().strftime('%A, %B %d, %Y')}
Capabilities: web search, data analysis, code generation, multi-language support.
Be helpful, accurate, and concise."""
        if context:
            import json
            base += f"\nContext: {json.dumps(context)}"
        return base

    def _gemini(self, system: str, prompt: str) -> str:
        try:
            from google.genai import types as gt
            full = f"{system}\n\nUser: {prompt}"
            resp = self.ai_client.models.generate_content(
                model=AI_PROVIDERS["gemini"]["model"],
                contents=full,
                config=gt.GenerateContentConfig(temperature=0.7, max_output_tokens=4096)
            )
            return resp.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return f"AI error: {e}"

    def get_capabilities(self) -> Dict:
        return {
            "provider": self.provider,
            "capabilities": ["web_search", "data_analysis", "code_generation",
                             "language_translation", "real_time_data"],
            "history_size": len(self.task_history),
        }

    def get_history(self, limit: int = 10) -> List[Dict]:
        return self.task_history[-limit:]

    def clear_memory(self):
        self.memory.clear()

    def _store(self, prompt: str, response: str):
        self.task_history.append({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response[:500],
            "provider": self.provider,
        })
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
