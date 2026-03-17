import asyncio
import os
import time
import traceback
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging

# Импортируем клинические случаи
from cases import case_1, case_2, case_3, case_4

# Список всех случаев и быстрый доступ по ID
all_cases = [case_1, case_2, case_3, case_4]
cases_by_id = {case['id']: case for case in all_cases}

# Проверка типов (выполняется при запуске)
print("Проверка типов случаев:")
for i, case in enumerate(all_cases):
    print(f"  case_{i+1}: {type(case)}")

# Загружаем переменные окружения из .env
load_dotenv()

# Отладочный вывод: что загрузилось
print("BOT_TOKEN =", os.getenv("BOT_TOKEN"))
print("OPENROUTER_API_KEY =", os.getenv("OPENROUTER_API_KEY"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Импортируем и инициализируем ИИ-клиент (после загрузки переменных)
from ai_client import AIClient
ai_client = AIClient()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния конечного автомата
class Simulator(StatesGroup):
    choosing_case = State()
    in_question = State()
    showing_result = State()
    ai_chat = State()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [
        [KeyboardButton(text="Начать симуляцию")],
        [KeyboardButton(text="Спросить ИИ-ассистента")],
        [KeyboardButton(text="О проекте")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "👋 Добро пожаловать в симулятор принятия клинических решений!\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# О проекте
@dp.message(lambda message: message.text == "О проекте")
async def about(message: types.Message):
    await message.answer(
        "Это дипломный проект — симулятор для врачей, работающих с пациентами с когнитивными расстройствами.\n"
        "Автор: [Линенко Андрей Валерьевич]\n"
        "Версия прототипа: 0.5 (с ИИ-ассистентом)"
    )

# Начать симуляцию – показываем список случаев
@dp.message(lambda message: message.text == "Начать симуляцию")
async def start_sim(message: types.Message, state: FSMContext):
    start_time = time.time()
    print("🟢 Нажата кнопка 'Начать симуляцию'")
    print(f"Количество случаев: {len(all_cases)}")
    for case in all_cases:
        print(f"  - {case['id']}: {case['title']}")

    try:
        buttons = [[KeyboardButton(text=f"Случай {case['id']}: {case['title']}")] for case in all_cases]
        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await state.set_state(Simulator.choosing_case)
        await message.answer("Выберите клинический случай:", reply_markup=keyboard)

    except Exception as e:
        print(f"❌ ОШИБКА в start_sim: {e}")
        traceback.print_exc()
        await message.answer("Произошла внутренняя ошибка. Попробуйте позже.")

    end_time = time.time()
    print(f"⏱ Время выполнения start_sim: {end_time - start_time:.3f} сек.")

# Выбор конкретного случая
@dp.message(Simulator.choosing_case)
async def case_chosen(message: types.Message, state: FSMContext):
    start_time = time.time()
    print(f"🔵 Выбран случай: {message.text}")

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        case_id = int(message.text.split(":")[0].split()[1])
    except (IndexError, ValueError):
        await message.answer("Не удалось распознать номер случая. Пожалуйста, выберите из списка.")
        return

    selected_case = cases_by_id.get(case_id)
    if not selected_case:
        await message.answer("Случай с таким номером не найден.")
        return

    print(f"Выбран случай: {selected_case['id']} - {selected_case['title']}")

    await state.update_data(case=selected_case, question_index=0, score=0)
    await state.set_state(Simulator.in_question)
    await send_question(message, state)

    end_time = time.time()
    print(f"⏱ Время выполнения case_chosen: {end_time - start_time:.3f} сек.")

# Отправка вопроса
async def send_question(message: types.Message, state: FSMContext):
    start_time = time.time()
    data = await state.get_data()
    case = data['case']
    idx = data['question_index']
    question = case['questions'][idx]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    buttons = [[KeyboardButton(text=opt)] for opt in question['options']]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer(
        f"**{case['title']}**\n\n{case['description']}\n\n**Вопрос {idx+1}:** {question['text']}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    end_time = time.time()
    print(f"⏱ Время отправки вопроса {idx+1}: {end_time - start_time:.3f} сек.")

# Обработка ответов на вопросы
@dp.message(Simulator.in_question)
async def handle_answer(message: types.Message, state: FSMContext):
    start_time = time.time()
    data = await state.get_data()
    case = data['case']
    idx = data['question_index']
    question = case['questions'][idx]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if message.text not in question['options']:
        await message.answer("Пожалуйста, выберите вариант из предложенных.")
        return

    selected_idx = question['options'].index(message.text)
    is_correct = (selected_idx == question['correct'])

    if is_correct:
        await state.update_data(score=data['score'] + 1)
        await message.answer(f"✅ Правильно!\n\n{question['explanation']}")
    else:
        correct_answer = question['options'][question['correct']]
        await message.answer(f"❌ Неправильно.\nПравильный ответ: {correct_answer}\n\n{question['explanation']}")

    if idx + 1 < len(case['questions']):
        await state.update_data(question_index=idx + 1)
        await send_question(message, state)
    else:
        score = data['score'] + (1 if is_correct else 0)
        total = len(case['questions'])
        await message.answer(
            f"**Симуляция завершена!**\n\nПравильных ответов: {score} из {total}\n\n"
            f"**Рекомендации:** {case['final_note']}",
            parse_mode="Markdown"
        )
        await state.clear()
        kb = [
            [KeyboardButton(text="Начать симуляцию")],
            [KeyboardButton(text="Спросить ИИ-ассистента")],
            [KeyboardButton(text="О проекте")]
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer("Выберите действие:", reply_markup=keyboard)

    end_time = time.time()
    print(f"⏱ Время обработки ответа на вопрос {idx+1}: {end_time - start_time:.3f} сек.")

# Обработчик кнопки "Спросить ИИ-ассистента"
@dp.message(lambda message: message.text == "Спросить ИИ-ассистента")
async def start_ai_chat(message: types.Message, state: FSMContext):
    print("🔍 start_ai_chat: проверяем доступность ИИ")
    print("   ai_client.is_available() =", ai_client.is_available())
    if not ai_client.is_available():
        await message.answer("Извините, ИИ-ассистент временно недоступен (нет API ключа).")
        return

    await state.set_state(Simulator.ai_chat)
    system_prompt = """Ты — медицинский ассистент, помогающий врачам в диагностике 
    когнитивных расстройств. Отвечай кратко, по делу, основываясь на современных 
    клинических рекомендациях. Если вопрос не по медицине, вежливо возвращай к теме."""
    
    await state.update_data(system_prompt=system_prompt)
    await message.answer(
        "🧑‍⚕️ **Режим ИИ-ассистента**\n\n"
        "Задайте любой вопрос по диагностике когнитивных нарушений, лечению деменций "
        "или интерпретации симптомов. Для выхода отправьте /end",
        parse_mode="Markdown"
    )

# Обработчик сообщений в режиме ИИ
@dp.message(Simulator.ai_chat)
async def handle_ai_chat(message: types.Message, state: FSMContext):
    if message.text == "/end":
        await state.clear()
        await cmd_start(message, state)
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    data = await state.get_data()
    system_prompt = data.get('system_prompt')

    response = await ai_client.get_response(message.text, system_prompt)
    await message.answer(response)

# Запуск бота
async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())