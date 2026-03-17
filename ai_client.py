# ai_client.py - Клиент для работы с OpenRouter API с автоматическим перебором моделей
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
        """Проверяет, доступен ли ИИ-клиент (наличие ключа)"""
        available = bool(self.api_key)
        print(f"🔍 is_available() вызван, результат: {available}")
        return available
    
    async def get_response(self, user_message, system_prompt=None):
        """Получить ответ от нейросети через OpenRouter с перебором моделей"""
        print(f"📤 get_response() вызван с сообщением: {user_message[:50]}...")
        
        if not self.api_key:
            print("❌ Ошибка: api_key отсутствует")
            return "❌ API ключ не настроен. Добавьте OPENROUTER_API_KEY в .env"
        
        # Список бесплатных моделей в порядке предпочтения (март 2026)
        models_to_try = [
            "qwen/qwen3-coder-480b-a35b:free",           # Qwen Coder – отличное качество
            "stepfun/step-3.5-flash:free",               # StepFun – быстрая
            "arcee-ai/trinity-large-preview:free",       # Arcee Trinity – мощная MoE
            "nvidia/nemotron-3-super-120b:free",         # NVIDIA Nemotron
            "openrouter/hunter-alpha:free",               # OpenRouter Hunter Alpha
            "z-ai/glm-4.5-air:free",                      # GLM-4.5 Air
            "openrouter/healer-alpha:free",               # Healer Alpha (омнимодальная)
            "meta-llama/llama-3.3-70b-instruct:free",     # LLaMA 3.3
            "google/gemma-2-2b-it:free"                   # Gemma 2 2B – лёгкая
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
        
        # Последовательно пробуем каждую модель
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
                            print(f"✅ Успешно с моделью: {model}")
                            return reply
                        else:
                            error_text = await resp.text()
                            print(f"⚠️ Модель {model} не сработала (статус {resp.status})")
                            print(f"   Ответ: {error_text[:200]}")
                            # Если это не 404 или 5xx, может быть проблема с ключом или форматированием
                            if resp.status in [401, 402, 403]:
                                return f"⚠️ Ошибка авторизации: {resp.status}. Проверьте ключ."
                            # Иначе продолжаем перебор
            except Exception as e:
                print(f"⚠️ Ошибка соединения с моделью {model}: {e}")
                continue
        
        # Если ни одна модель не сработала
        return "❌ К сожалению, ни одна из моделей сейчас не доступна. Попробуйте позже."