# ai_client.py - Клиент для работы с OpenRouter API (исправленная версия)
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
        """Проверяет, доступен ли ИИ-клиент"""
        available = bool(self.api_key)
        print(f"🔍 is_available() вызван, результат: {available}")
        return available
    
    async def get_response(self, user_message, system_prompt=None):
        print(f"📤 get_response() вызван с сообщением: {user_message[:50]}...")
        if not self.api_key:
            print("❌ Ошибка: api_key отсутствует")
            return "❌ API ключ не настроен. Добавьте OPENROUTER_API_KEY в .env"
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Используем актуальную бесплатную модель
        model = "meta-llama/llama-3.3-70b-instruct:free"
        
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
        
        print(f"📡 Отправка запроса к OpenRouter с моделью: {model}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    print(f"📥 Статус ответа: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data["choices"][0]["message"]["content"]
                        print(f"✅ Ответ получен, длина: {len(reply)} символов")
                        return reply
                    else:
                        error_text = await resp.text()
                        print(f"❌ Ошибка API: {resp.status} - {error_text}")
                        try:
                            error_json = json.loads(error_text)
                            if "error" in error_json:
                                error_msg = error_json["error"].get("message", "")
                                if "model not found" in error_msg.lower():
                                    return f"⚠️ Модель '{model}' не найдена. Попробуйте другую модель в коде."
                                return f"⚠️ Ошибка OpenRouter: {error_msg}"
                        except:
                            pass
                        return f"⚠️ Ошибка API: {resp.status}. Проверьте ключ или попробуйте позже."
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            return f"⚠️ Ошибка соединения: {str(e)}"