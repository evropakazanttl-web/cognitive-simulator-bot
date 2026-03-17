# ai_client.py - Клиент для работы с OpenRouter API (с перебором моделей)
import os
import aiohttp
import json

class AIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if self.api_key:
            print("✅ ИИ-клиент инициализирован (OpenRouter)")
            print(f"   Ключ (первые 10 символов): {self.api_key[:10]}...")
        else:
            print("⚠️ ВНИМАНИЕ: OPENROUTER_API_KEY не найден в .env")
    
    def is_available(self):
        return bool(self.api_key)
    
    async def get_response(self, user_message, system_prompt=None):
        if not self.api_key:
            return "❌ API ключ не настроен. Добавьте OPENROUTER_API_KEY в .env"
        
        # Список бесплатных моделей в порядке предпочтения (март 2026)
        models_to_try = [
            "qwen/qwen3-coder-480b-a35b:free",
            "stepfun/step-3.5-flash:free",
            "arcee-ai/trinity-large-preview:free",
            "nvidia/nemotron-3-super-120b:free",
            "openrouter/hunter-alpha:free",
            "z-ai/glm-4.5-air:free",
            "openrouter/healer-alpha:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-2b-it:free"
        ]
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        for model in models_to_try:
            print(f"🔄 Пробуем модель: {model}")
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["choices"][0]["message"]["content"]
                        else:
                            print(f"⚠️ Модель {model} не сработала (статус {resp.status})")
            except Exception as e:
                print(f"⚠️ Ошибка с моделью {model}: {e}")
                continue
        
        return "❌ К сожалению, ни одна из моделей сейчас не доступна. Попробуйте позже."