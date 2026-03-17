import asyncio
import os
import time
import traceback
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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

# Импортируем и инициализируем ИИ-клиент
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

# ---------- Функции для создания клавиатур ----------
def main_menu_keyboard():
    """Главное меню с inline-кнопками"""
    buttons = [
        [InlineKeyboardButton(text="🎲 Начать симуляцию", callback_data="start_sim")],
        [InlineKeyboardButton(text="🤖 Спросить ИИ-ассистента", callback_data="start_ai")],
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cases_keyboard():
    """Клавиатура со списком клинических случаев"""
    buttons = []
    for case in all_cases:
        buttons.append([InlineKeyboardButton(
            text=f"🧠 Случай {case['id']}: {case['title']}",
            callback_data=f"case_{case['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def question_keyboard(options):
    """Клавиатура с вариантами ответов на вопрос"""
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(text=opt, callback_data=f"answer_{opt}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ai_chat_keyboard():
    """Клавиатура в режиме ИИ-ассистента (кнопка выхода)"""
    buttons = [[InlineKeyboardButton(text="🚪 Выйти из режима ИИ", callback_data="exit_ai")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Добро пожаловать в симулятор принятия клинических решений!</b>\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

# ---------- Обработчики callback'ов ----------
@dp.callback_query(lambda c: c.data == "about")
async def callback_about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "ℹ️ <b>О проекте</b>\n\n"
        "Это дипломный проект — симулятор для врачей, работающих с пациентами с когнитивными расстройствами.\n"
        "Автор: Линенко Андрей Валерьевич\n"
        "Версия: 1.0 (с ИИ-ассистентом)",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "start_sim")
async def callback_start_sim(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📋 <b>Выберите клинический случай:</b>",
        reply_markup=cases_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(Simulator.choosing_case)

@dp.callback_query(Simulator.choosing_case, lambda c: c.data.startswith("case_"))
async def callback_case_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    case_id = int(callback.data.split("_")[1])
    selected_case = cases_by_id.get(case_id)
    if not selected_case:
        await callback.message.edit_text("❌ Случай не найден.")
        return

    await state.update_data(case=selected_case, question_index=0, score=0)
    await state.set_state(Simulator.in_question)
    await send_question(callback.message, state)

@dp.callback_query(Simulator.in_question, lambda c: c.data.startswith("answer_"))
async def callback_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    answer_text = callback.data[7:]  # удаляем "answer_"
    data = await state.get_data()
    case = data['case']
    idx = data['question_index']
    question = case['questions'][idx]

    if answer_text not in question['options']:
        await callback.message.answer("❌ Пожалуйста, выберите вариант из предложенных.")
        return

    selected_idx = question['options'].index(answer_text)
    is_correct = (selected_idx == question['correct'])

    # Формируем сообщение с обратной связью
    if is_correct:
        await state.update_data(score=data['score'] + 1)
        feedback = f"✅ <b>Правильно!</b>\n\n{question['explanation']}"
    else:
        correct_answer = question['options'][question['correct']]
        feedback = f"❌ <b>Неправильно.</b>\n\nПравильный ответ: <b>{correct_answer}</b>\n\n{question['explanation']}"

    await callback.message.edit_text(feedback, parse_mode="HTML")

    # Переходим к следующему вопросу или завершаем
    if idx + 1 < len(case['questions']):
        await state.update_data(question_index=idx + 1)
        await send_question(callback.message, state)
    else:
        score = data['score'] + (1 if is_correct else 0)
        total = len(case['questions'])
        await callback.message.answer(
            f"🏁 <b>Симуляция завершена!</b>\n\n"
            f"Правильных ответов: {score} из {total}\n\n"
            f"<b>Рекомендации:</b> {case['final_note']}",
            parse_mode="HTML"
        )
        await state.clear()
        await callback.message.answer(
            "👋 Выберите действие:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

# ---------- Вспомогательная функция отправки вопроса ----------
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    case = data['case']
    idx = data['question_index']
    question = case['questions'][idx]

    await message.edit_text(
        f"🧠 <b>{case['title']}</b>\n\n"
        f"📋 <i>{case['description']}</i>\n\n"
        f"❓ <b>Вопрос {idx+1}:</b> {question['text']}",
        reply_markup=question_keyboard(question['options']),
        parse_mode="HTML"
    )

# ---------- Обработчики для ИИ-ассистента ----------
@dp.callback_query(lambda c: c.data == "start_ai")
async def callback_start_ai(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not ai_client.is_available():
        await callback.message.edit_text(
            "❌ Извините, ИИ-ассистент временно недоступен (нет API ключа).",
            reply_markup=main_menu_keyboard()
        )
        return

    await state.set_state(Simulator.ai_chat)
    system_prompt = """Ты — медицинский ассистент, помогающий врачам в диагностике 
    когнитивных расстройств. Отвечай кратко, по делу, основываясь на современных 
    клинических рекомендациях. Если вопрос не по медицине, вежливо возвращай к теме."""
    
    await state.update_data(system_prompt=system_prompt)
    await callback.message.edit_text(
        "🧑‍⚕️ <b>Режим ИИ-ассистента</b>\n\n"
        "Задайте любой вопрос по диагностике когнитивных нарушений, лечению деменций "
        "или интерпретации симптомов. Для выхода нажмите кнопку ниже или отправьте /end",
        reply_markup=ai_chat_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "exit_ai")
async def callback_exit_ai(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "👋 Выберите действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Simulator.ai_chat)
async def handle_ai_chat(message: types.Message, state: FSMContext):
    if message.text == "/end":
        await state.clear()
        await message.answer(
            "👋 Выберите действие:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    # Отправляем статус "печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    data = await state.get_data()
    system_prompt = data.get('system_prompt')

    response = await ai_client.get_response(message.text, system_prompt)
    await message.answer(response, parse_mode="HTML")

# ---------- Запуск бота ----------
async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())