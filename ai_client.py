# ai_client.py - Клиент для работы с OpenRouter API
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
        """Проверяет, доступен ли ИИ-клиент"""
        return bool(self.api_key)
    
    async def get_response(self, user_message, system_prompt=None):
        """Получить ответ от нейросети через OpenRouter"""
        
        if not self.api_key:
            return "❌ API ключ не настроен. Добавьте OPENROUTER_API_KEY в .env"
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Используем бесплатную модель Mistral 7B
        model = "mistralai/mistral-7b-instruct:free"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
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
                        error_text = await resp.text()
                        print(f"Ошибка API: {resp.status} - {error_text}")
                        return f"⚠️ Ошибка API: {resp.status}. Проверьте ключ или попробуйте позже."
        except Exception as e:
            print(f"Ошибка соединения: {e}")
            return f"⚠️ Ошибка соединения: {str(e)}"