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

# Для прокси – проверяем наличие библиотеки
try:
    from aiogram.client.session.aiohttp import AiohttpSession
    import aiohttp_socks
    PROXY_SUPPORT = True
except ImportError:
    PROXY_SUPPORT = False
    print("⚠️ Библиотека aiohttp-socks не установлена. Прокси не будут работать.")

# Импортируем клинические случаи
from cases import case_1, case_2, case_3, case_4

all_cases = [case_1, case_2, case_3, case_4]
cases_by_id = {case['id']: case for case in all_cases}

print("Проверка типов случаев:")
for i, case in enumerate(all_cases):
    print(f"  case_{i+1}: {type(case)}")

load_dotenv()
print("BOT_TOKEN =", os.getenv("BOT_TOKEN"))
print("OPENROUTER_API_KEY =", os.getenv("OPENROUTER_API_KEY"))
print("PROXY_URL =", os.getenv("PROXY_URL"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")

from ai_client import AIClient
ai_client = AIClient()

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Simulator(StatesGroup):
    choosing_case = State()
    in_question = State()
    showing_result = State()
    ai_chat = State()

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 Начать симуляцию", callback_data="start_sim")],
        [InlineKeyboardButton(text="🤖 Спросить ИИ-ассистента", callback_data="start_ai")],
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cases_keyboard():
    buttons = []
    for case in all_cases:
        buttons.append([InlineKeyboardButton(
            text=f"🧠 Случай {case['id']}: {case['title']}",
            callback_data=f"case_{case['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def question_keyboard(options):
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(text=opt, callback_data=f"answer_{opt}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ai_chat_keyboard():
    buttons = [[InlineKeyboardButton(text="🚪 Выйти из режима ИИ", callback_data="exit_ai")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    print("🚀 /start вызван")
    await state.clear()
    await message.answer(
        "👋 <b>Добро пожаловать в симулятор принятия клинических решений!</b>\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "about")
async def callback_about(callback: CallbackQuery):
    print("ℹ️ about callback")
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
    print("🟢 callback_start_sim вызван")
    await callback.answer()
    await callback.message.edit_text(
        "📋 <b>Выберите клинический случай:</b>",
        reply_markup=cases_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(Simulator.choosing_case)
    print(f"Состояние установлено: {await state.get_state()}")

@dp.callback_query(Simulator.choosing_case, lambda c: c.data.startswith("case_"))
async def callback_case_chosen(callback: CallbackQuery, state: FSMContext):
    print(f"🔵 callback_case_chosen: {callback.data}")
    await callback.answer()
    case_id = int(callback.data.split("_")[1])
    selected_case = cases_by_id.get(case_id)
    if not selected_case:
        await callback.message.edit_text("❌ Случай не найден.")
        return

    await state.update_data(case=selected_case, question_index=0, score=0)
    await state.set_state(Simulator.in_question)
    print(f"Состояние после выбора: {await state.get_state()}")
    await send_question_new(callback.message, state)

@dp.callback_query(Simulator.in_question, lambda c: c.data.startswith("answer_"))
async def callback_answer(callback: CallbackQuery, state: FSMContext):
    print(f"📝 callback_answer: {callback.data}")
    await callback.answer()
    answer_text = callback.data[7:]  # удаляем "answer_"
    data = await state.get_data()
    case = data.get('case')
    idx = data.get('question_index', 0)
    if case is None:
        print("❌ Ошибка: case не найден в state")
        await callback.message.answer("❌ Ошибка состояния. Попробуйте /start заново.")
        await state.clear()
        return

    if idx >= len(case['questions']):
        print(f"❌ Ошибка: индекс {idx} вне диапазона (всего {len(case['questions'])})")
        await callback.message.answer("❌ Ошибка: вы уже прошли все вопросы. Начните заново.")
        await state.clear()
        return

    question = case['questions'][idx]
    print(f"Текущий индекс: {idx}, всего вопросов: {len(case['questions'])}")

    if answer_text not in question['options']:
        await callback.message.answer("❌ Пожалуйста, выберите вариант из предложенных.")
        return

    selected_idx = question['options'].index(answer_text)
    is_correct = (selected_idx == question['correct'])

    if is_correct:
        await state.update_data(score=data.get('score', 0) + 1)
        feedback = f"✅ <b>Правильно!</b>\n\n{question['explanation']}"
    else:
        correct_answer = question['options'][question['correct']]
        feedback = f"❌ <b>Неправильно.</b>\n\nПравильный ответ: <b>{correct_answer}</b>\n\n{question['explanation']}"

    await callback.message.edit_text(feedback, parse_mode="HTML")

    if idx + 1 < len(case['questions']):
        new_idx = idx + 1
        await state.update_data(question_index=new_idx)
        print(f"Индекс обновлён на {new_idx}")
        print(f"Переходим к вопросу {new_idx+1}")
        await send_question_new(callback.message, state)
    else:
        score = data.get('score', 0) + (1 if is_correct else 0)
        total = len(case['questions'])
        print("Симуляция завершена")
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

async def send_question_new(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        case = data.get('case')
        if case is None:
            print("❌ Ошибка в send_question_new: case не найден в state")
            return
        idx = data.get('question_index', 0)
        if idx >= len(case['questions']):
            print(f"❌ Ошибка в send_question_new: индекс {idx} вне диапазона ({len(case['questions'])})")
            return
        question = case['questions'][idx]
        print(f"📤 send_question_new вызван для вопроса index={idx+1}")
        await message.answer(
            f"🧠 <b>{case['title']}</b>\n\n"
            f"📋 <i>{case['description']}</i>\n\n"
            f"❓ <b>Вопрос {idx+1}:</b> {question['text']}",
            reply_markup=question_keyboard(question['options']),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Ошибка в send_question_new: {e}")
        import traceback
        traceback.print_exc()

@dp.callback_query(lambda c: c.data == "start_ai")
async def callback_start_ai(callback: CallbackQuery, state: FSMContext):
    print("🤖 callback_start_ai вызван")
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
    print("🚪 exit_ai вызван")
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
        print("Выход из ИИ по /end")
        await state.clear()
        await message.answer(
            "👋 Выберите действие:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    data = await state.get_data()
    system_prompt = data.get('system_prompt')

    response = await ai_client.get_response(message.text, system_prompt)
    await message.answer(response, parse_mode="HTML")

async def create_bot():
    if PROXY_URL and PROXY_SUPPORT:
        print(f"🔌 Используем прокси: {PROXY_URL}")
        try:
            session = AiohttpSession(proxy=PROXY_URL)
            return Bot(token=BOT_TOKEN, session=session)
        except Exception as e:
            print(f"❌ Ошибка подключения прокси: {e}")
            print("⚠️ Запускаем без прокси")
            return Bot(token=BOT_TOKEN)
    else:
        if PROXY_URL and not PROXY_SUPPORT:
            print("⚠️ Указан PROXY_URL, но библиотека aiohttp-socks не установлена. Установите: pip install aiohttp-socks")
        else:
            print("⚠️ Прокси не задан, работаем напрямую (может не работать из РФ)")
        return Bot(token=BOT_TOKEN)

bot = None

async def main():
    global bot
    bot = await create_bot()
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())