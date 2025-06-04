import logging
import os
import sys
import json
from dataclasses import dataclass
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class Animal:
    name: str
    description: str
    image_url: str
    traits: List[str] = None
    adoption_info: str = ""
    
    def __post_init__(self):
        if self.traits is None:
            self.traits = []

# Load data
def load_animals():
    try:
        with open('data/animals.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [Animal(**animal) for animal in data]
    except FileNotFoundError:
        # Fallback animals if file not found
        return [
            Animal("Амурский тигр", "Величественный хищник", "", ["Сильный", "Независимый"]),
            Animal("Красная панда", "Милый пушистый зверёк", "", ["Игривый", "Спокойный"]),
            Animal("Снежный барс", "Неуловимый горный хищник", "", ["Ловкий", "Загадочный"]),
        ]

def load_questions():
    try:
        with open('data/questions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback questions
        return [
            {
                "question": "Какое время дня вам больше нравится?",
                "answers": ["🌅 Утро", "☀️ День", "🌙 Вечер", "🌃 Ночь"]
            },
            {
                "question": "Где бы вы хотели жить?",
                "answers": ["🏔️ Горы", "🌲 Лес", "🏖️ У воды", "🏜️ Пустыня"]
            }
        ]

# Global data
ANIMALS = load_animals()
QUESTIONS = load_questions()

# Handlers
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user = update.effective_user
    
    welcome_text = f"""🦁 Добро пожаловать, {user.first_name}!

🎪 **Викторина "Какое ваше тотемное животное?"**

Пройдите увлекательную викторину и узнайте, с каким обитателем Московского зоопарка у вас больше всего общего!

🎯 Отвечайте честно на вопросы, и мы подберём для вас идеальное животное.

Готовы начать?"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Начать викторину", callback_data="start_quiz")],
        [InlineKeyboardButton("ℹ️ О программе опеки", callback_data="about_program")],
        [InlineKeyboardButton("📞 Связаться с зоопарком", callback_data="contact")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the quiz."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['questions'] = QUESTIONS
    context.user_data['current_question'] = 0
    context.user_data['answers'] = []
    
    await show_question(update, context)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current question."""
    questions = context.user_data['questions']
    current_q = context.user_data['current_question']
    
    if current_q >= len(questions):
        await show_result(update, context)
        return
    
    question = questions[current_q]
    
    question_text = f"❓ **Вопрос {current_q + 1} из {len(questions)}**\n\n{question['question']}"
    
    keyboard = []
    for i, answer in enumerate(question['answers']):
        keyboard.append([InlineKeyboardButton(answer, callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            question_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz answers."""
    query = update.callback_query
    await query.answer()
    
    answer_index = int(query.data.split('_')[1])
    
    context.user_data['answers'].append(answer_index)
    context.user_data['current_question'] += 1
    
    await show_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz result."""
    query = update.callback_query
    answers = context.user_data['answers']
    
    # Calculate result
    total_score = sum(answers)
    animal_index = total_score % len(ANIMALS)
    result_animal = ANIMALS[animal_index]
    
    # Store result
    context.user_data['result_animal'] = result_animal
    
    result_message = f"🎯 **Ваше тотемное животное: {result_animal.name}!**\n\n"
    result_message += f"📖 {result_animal.description}\n\n"
    
    if result_animal.traits:
        result_message += "✨ **Ваши качества:**\n"
        for trait in result_animal.traits[:3]:
            result_message += f"• {trait}\n"
        result_message += "\n"
    
    result_message += "🤝 **Хотите стать опекуном?**\n"
    result_message += "Программа опеки Московского зоопарка позволяет вам поддержать любимое животное!"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="start_quiz")],
        [InlineKeyboardButton("📤 Поделиться", callback_data="share_result")],
        [InlineKeyboardButton("🤝 Стать опекуном", callback_data="become_guardian")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_message, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def about_program_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle about program."""
    query = update.callback_query
    await query.answer()
    
    about_text = """🤝 **Программа опеки Московского зоопарка**

Станьте опекуном животного и помогите зоопарку!

**Что вы получите:**
🎁 Именной сертификат опекуна
📱 Эксклюзивные фото и видео
📧 Регулярные отчёты
🎟 Льготные билеты
👥 Закрытые мероприятия

Узнать больше: https://moscowzoo.ru"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Пройти викторину", callback_data="start_quiz")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(about_text, reply_markup=reply_markup, parse_mode='Markdown')

async def share_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sharing."""
    query = update.callback_query
    await query.answer()
    
    result_animal = context.user_data.get('result_animal')
    if not result_animal:
        await query.edit_message_text("Ошибка: пройдите викторину заново.")
        return
    
    share_text = f"🎯 Я прошёл викторину зоопарка!\nМоё тотемное животное: {result_animal.name}"
    
    keyboard = [
        [InlineKeyboardButton("📱 Поделиться", 
                            url=f"https://t.me/share/url?text={share_text}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Поделитесь результатом:", reply_markup=reply_markup)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact."""
    query = update.callback_query
    await query.answer()
    
    contact_text = """📞 **Связь с Московским зоопарком**

📧 Email: info@moscowzoo.ru
📱 Телефон: +7 (495) 255-53-75
🌐 Сайт: moscowzoo.ru
📍 Адрес: Большая Грузинская ул., 1

🕘 Режим работы: Пн-Вс 9:00-17:00"""
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(contact_text, reply_markup=reply_markup, parse_mode='Markdown')

async def become_guardian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle becoming guardian."""
    query = update.callback_query
    await query.answer()
    
    guardian_text = """🤝 **Стать опекуном**

Поддержите животных зоопарка!
Узнайте больше на сайте зоопарка.

🌐 moscowzoo.ru/guardianship"""
    
    keyboard = [
        [InlineKeyboardButton("🌐 Перейти на сайт", url="https://moscowzoo.ru")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_result")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(guardian_text, reply_markup=reply_markup, parse_mode='Markdown')

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(about_program_handler, pattern="^about_program$"))
    application.add_handler(CallbackQueryHandler(start_quiz_handler, pattern="^start_quiz$"))
    application.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer_\\d+$"))
    application.add_handler(CallbackQueryHandler(share_result_handler, pattern="^share_result$"))
    application.add_handler(CallbackQueryHandler(contact_handler, pattern="^contact$"))
    application.add_handler(CallbackQueryHandler(become_guardian_handler, pattern="^become_guardian$"))
    
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()