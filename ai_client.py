# ai_client.py - Клиент для работы с OpenRouter API (с поддержкой Gemini как резерв)
import os
import aiohttp
import json

class AIClient:
    def __init__(self):
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.openrouter_key:
            print("✅ ИИ-клиент инициализирован (OpenRouter)")
        elif self.gemini_key:
            print("✅ ИИ-клиент инициализирован (Google Gemini)")
        else:
            print("⚠️ ВНИМАНИЕ: ни один API ключ не найден в .env")
    
    def is_available(self):
        """Проверяет, доступен ли ИИ-клиент (есть хотя бы один ключ)"""
        return bool(self.openrouter_key or self.gemini_key)
    
    async def get_response(self, user_message, system_prompt=None):
        """Получить ответ от нейросети. Сначала пробует OpenRouter, при ошибке - Gemini."""
        
        if self.openrouter_key:
            response = await self._query_openrouter(user_message, system_prompt)
            if response and not response.startswith("⚠️ Ошибка"):
                return response
            # Если OpenRouter вернул ошибку, пробуем Gemini
            print("OpenRouter недоступен, пробуем Gemini...")
        
        if self.gemini_key:
            return await self._query_gemini(user_message, system_prompt)
        
        return "❌ Нейросеть временно недоступна. Проверьте API ключи в .env"
    
    async def _query_openrouter(self, user_message, system_prompt):
        """Запрос к OpenRouter API с актуальной бесплатной моделью"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Используем актуальную бесплатную модель (март 2026)
        model = "google/gemma-2-9b-it:free"  # или "meta-llama/llama-3-8b-instruct:free"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
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
                        print(f"Ошибка OpenRouter: {resp.status} - {error_text}")
                        return f"⚠️ Ошибка OpenRouter: {resp.status}. Проверьте ключ или попробуйте позже."
        except Exception as e:
            print(f"Ошибка соединения с OpenRouter: {e}")
            return f"⚠️ Ошибка соединения: {str(e)}"
    
    async def _query_gemini(self, user_message, system_prompt):
        """Запрос к Google Gemini API (бесплатный, 60 запросов/мин)"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        
        # Формируем промпт с системным сообщением
        full_prompt = f"{system_prompt}\n\nВопрос: {user_message}" if system_prompt else user_message
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "candidates" in data:
                            return data["candidates"][0]["content"]["parts"][0]["text"]
                        else:
                            return "⚠️ Неожиданный ответ от Gemini"
                    else:
                        error_text = await resp.text()
                        print(f"Ошибка Gemini: {resp.status} - {error_text}")
                        return f"⚠️ Ошибка Gemini: {resp.status}. Проверьте ключ."
        except Exception as e:
            print(f"Ошибка соединения с Gemini: {e}")
            return f"⚠️ Ошибка соединения: {str(e)}"