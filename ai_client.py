import os
import aiohttp
import json

class AIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if self.api_key:
            print("✅ ИИ-клиент инициализирован (OpenRouter)")
        else:
            print("⚠️ ВНИМАНИЕ: OPENROUTER_API_KEY не найден в .env")
    
    def is_available(self):
        return bool(self.api_key)

    async def get_response(self, user_message, system_prompt=None):
        if not self.api_key:
            return "❌ API ключ не настроен. Добавьте OPENROUTER_API_KEY в .env"
        
        # Расширенный список рабочих бесплатных моделей
        models_to_try = [
            "google/gemma-2-9b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen2.5-72b-instruct:free",
            "microsoft/phi-4:free"
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
                        print(f"📥 Статус ответа: {resp.status}")
                        if resp.status == 200:
                            data = await resp.json()
                            reply = data["choices"][0]["message"]["content"]
                            print(f"✅ Ответ получен от модели: {model}")
                            return reply
                        else:
                            error_text = await resp.text()
                            print(f"⚠️ Модель {model} не сработала (статус {resp.status}): {error_text[:200]}")
            except Exception as e:
                print(f"⚠️ Ошибка соединения с моделью {model}: {e}")
        
        return "❌ К сожалению, ни одна из моделей сейчас не доступна. Попробуйте позже."