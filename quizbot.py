import telebot
from telebot import types
import random
import time
import pandas as pd
import docx
import PyPDF2
import os
from datetime import datetime
import signal
import sys
import logging

# Logging sozlamalari
logging.basicConfig(
    filename='bot.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Bot tokeni - o'zingizning tokeningizni qo'ying
TOKEN = "8175153004:AAHtg3VJQzFeD26NceTrgKUCWfVp44iEJho"

# Bot obyektini yaratish
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchilar ma'lumotlarini saqlash
user_data = {}

class UserState:
    def __init__(self):
        self.dictionary = {}
        self.current_quiz = []
        self.score = 0
        self.current_question = 0
        self.quiz_start_time = None
        self.question_start_time = None

# Xavfsiz xabar yuborish funksiyasi
def safe_send_message(chat_id, text, reply_markup=None):
    try:
        for _ in range(3):  # 3 marta urinish
            try:
                return bot.send_message(
                    chat_id=chat_id, 
                    text=text, 
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except telebot.apihelper.ApiException as e:
                if "429" in str(e):  # Too Many Requests
                    time.sleep(1)
                    continue
                raise
        return None
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {str(e)}")
        return None

# Start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        user_data[user_id] = UserState()
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📝 So'zlarni kiritish", "📝 Ko'p so'z kiritish")
        markup.row("📁 File yuklash")
        
        welcome_text = (
            "🎯 <b>Quiz Bot</b>ga xush kelibsiz!\n\n"
            "Bot imkoniyatlari:\n"
            "1. So'zlarni bittadan kiritish\n"
            "2. Ko'p so'zlarni bir vaqtda kiritish\n"
            "3. Fayl (.txt, .xlsx, .docx, .pdf) yuklash\n"
            "4. Quiz o'yini (10, 20, 30 ta savol)\n"
            "5. Har bir savolga 10 soniya vaqt\n\n"
            "Boshlash uchun quyidagi tugmalardan birini tanlang 👇"
        )
        
        safe_send_message(message.chat.id, welcome_text, markup)
        logger.info(f"Yangi foydalanuvchi: {user_id}")
    except Exception as e:
        logger.error(f"Start komandasi xatosi: {e}")

# So'z kiritish
@bot.message_handler(func=lambda message: message.text == "📝 So'zlarni kiritish")
def input_word(message):
    try:
        instruction = (
            "So'z va tarjimasini quyidagi formatda kiriting:\n\n"
            "<b>so'z - tarjima</b>\n\n"
            "Masalan: apple - olma\n\n"
            "Quiz'ni boshlash uchun 'quiz' so'zini yuboring."
        )
        safe_send_message(message.chat.id, instruction)
        bot.register_next_step_handler(message, process_word)
    except Exception as e:
        logger.error(f"So'z kiritish xatosi: {e}")

def process_word(message):
    try:
        user_id = message.from_user.id
        if message.text.lower() == 'quiz':
            ask_question_count(message)
            return
            
        if '-' in message.text:
            word, translation = message.text.split('-', 1)
            word = word.strip().lower()
            translation = translation.strip().lower()
            
            if word and translation:
                user_data[user_id].dictionary[word] = translation
                response = (
                    "✅ So'z qo'shildi!\n\n"
                    "Yana so'z qo'shish uchun xuddi shunday formatda yuboring.\n"
                    "Quiz'ni boshlash uchun 'quiz' so'zini yuboring."
                )
            else:
                response = "❌ So'z yoki tarjima bo'sh bo'lishi mumkin emas!"
        else:
            response = (
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format: <b>so'z - tarjima</b>\n"
                "Masalan: apple - olma"
            )
            
        safe_send_message(message.chat.id, response)
        bot.register_next_step_handler(message, process_word)
    except Exception as e:
        logger.error(f"So'zni qayta ishlashda xatolik: {e}")

# Ko'p so'z kiritish
@bot.message_handler(func=lambda message: message.text == "📝 Ko'p so'z kiritish")
def input_many_words(message):
    try:
        instruction = (
            "So'zlarni quyidagi formatda kiriting:\n\n"
            "apple - olma\n"
            "book - kitob\n"
            "cat - mushuk\n"
            "dog - it\n\n"
            "Har bir so'z yangi qatordan yozilishi kerak!\n"
            "Quiz'ni boshlash uchun 'quiz' so'zini yuboring."
        )
        safe_send_message(message.chat.id, instruction)
        bot.register_next_step_handler(message, process_many_words)
    except Exception as e:
        logger.error(f"Ko'p so'z kiritish xatosi: {e}")
def process_many_words(message):
    try:
        user_id = message.from_user.id
        if message.text.lower() == 'quiz':
            ask_question_count(message)
            return
        
        lines = message.text.strip().split('\n')
        added_words = 0
        failed_words = 0
        
        for line in lines:
            if '-' in line:
                word, translation = line.split('-', 1)
                word = word.strip().lower()
                translation = translation.strip().lower()
                
                if word and translation:
                    user_data[user_id].dictionary[word] = translation
                    added_words += 1
                else:
                    failed_words += 1
            else:
                failed_words += 1
        
        response = []
        if added_words > 0:
            response.append(f"✅ {added_words} ta so'z muvaffaqiyatli qo'shildi")
        if failed_words > 0:
            response.append(f"❌ {failed_words} ta so'z noto'g'ri formatda")
        
        response.append("\nYana so'z qo'shish uchun xuddi shunday formatda yuboring.")
        response.append("Quiz'ni boshlash uchun 'quiz' so'zini yuboring.")
        
        safe_send_message(message.chat.id, "\n".join(response))
        bot.register_next_step_handler(message, process_many_words)
        
        logger.info(f"Foydalanuvchi {user_id}: {added_words} ta so'z qo'shildi")
    except Exception as e:
        logger.error(f"So'zlarni qayta ishlashda xatolik: {e}")
# File yuklash funksiyasi
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Fayl formati tekshiruvi
        if file_extension not in ['.txt', '.xlsx', '.docx', '.pdf']:
            safe_send_message(
                message.chat.id,
                "❌ Noto'g'ri fayl formati!\n\n"
                "Quyidagi formatlar qo'llab-quvvatlanadi:\n"
                "- .txt (matn fayli)\n"
                "- .xlsx (Excel fayli)\n"
                "- .docx (Word fayli)\n"
                "- .pdf (PDF fayli)"
            )
            return
        
        safe_send_message(message.chat.id, "📥 Fayl yuklanmoqda...")
        
        # Faylni yuklash
        downloaded_file = bot.download_file(file_info.file_path)
        user_id = message.from_user.id
        
        # Faylni qayta ishlash
        words_count = process_file(downloaded_file, file_extension, user_id)
        
        if words_count > 0:
            safe_send_message(
                message.chat.id,
                f"✅ Fayl muvaffaqiyatli yuklandi!\n"
                f"📚 {words_count} ta so'z qo'shildi.\n\n"
                f"Quiz'ni boshlash uchun 'quiz' so'zini yuboring."
            )
            # Quiz boshlash uchun so'rov
            ask_question_count(message)
        else:
            safe_send_message(
                message.chat.id,
                "❌ Faylda so'zlar topilmadi yoki format noto'g'ri.\n"
                "So'zlar quyidagi formatda bo'lishi kerak:\n"
                "so'z - tarjima"
            )
            
    except Exception as e:
        logger.error(f"Fayl yuklashda xatolik: {e}")
        safe_send_message(
            message.chat.id,
            "❌ Faylni yuklashda xatolik yuz berdi.\n"
            "Iltimos, qaytadan urinib ko'ring."
        )

def process_file(file_content, file_extension, user_id):
    """Faylni qayta ishlash"""
    try:
        words_count = 0
        
        if file_extension == '.txt':
            words_count = process_txt_file(file_content, user_id)
        elif file_extension == '.xlsx':
            words_count = process_excel_file(file_content, user_id)
        elif file_extension == '.docx':
            words_count = process_docx_file(file_content, user_id)
        elif file_extension == '.pdf':
            words_count = process_pdf_file(file_content, user_id)
            
        return words_count
    except Exception as e:
        logger.error(f"Faylni qayta ishlashda xatolik: {e}")
        return 0

def process_txt_file(file_content, user_id):
    """TXT faylni qayta ishlash"""
    try:
        content = file_content.decode('utf-8')
        lines = content.split('\n')
        words_count = 0
        
        for line in lines:
            if '-' in line:
                word, translation = line.split('-', 1)
                word = word.strip().lower()
                translation = translation.strip().lower()
                
                if word and translation:
                    user_data[user_id].dictionary[word] = translation
                    words_count += 1
                    
        return words_count
    except Exception as e:
        logger.error(f"TXT faylni qayta ishlashda xatolik: {e}")
        return 0

def process_excel_file(file_content, user_id):
    """Excel faylni qayta ishlash"""
    try:
        # Vaqtinchalik fayl yaratish
        temp_file = f"temp_{user_id}.xlsx"
        with open(temp_file, 'wb') as f:
            f.write(file_content)
            
        # Excel faylni o'qish
        df = pd.read_excel(temp_file)
        words_count = 0
        
        # Birinchi va ikkinchi ustunni o'qish
        for index, row in df.iterrows():
            if pd.notna(row[0]) and pd.notna(row[1]):
                word = str(row[0]).strip().lower()
                translation = str(row[1]).strip().lower()
                
                if word and translation:
                    user_data[user_id].dictionary[word] = translation
                    words_count += 1
                    
        # Vaqtinchalik faylni o'chirish
        os.remove(temp_file)
        return words_count
        
    except Exception as e:
        logger.error(f"Excel faylni qayta ishlashda xatolik: {e}")
        if os.path.exists(f"temp_{user_id}.xlsx"):
            os.remove(f"temp_{user_id}.xlsx")
        return 0

def process_docx_file(file_content, user_id):
    """DOCX faylni qayta ishlash"""
    try:
        # Vaqtinchalik fayl yaratish
        temp_file = f"temp_{user_id}.docx"
        with open(temp_file, 'wb') as f:
            f.write(file_content)
            
        # DOCX faylni o'qish
        doc = docx.Document(temp_file)
        words_count = 0
        
        # Har bir paragrafni o'qish
        for paragraph in doc.paragraphs:
            line = paragraph.text.strip()
            if '-' in line:
                word, translation = line.split('-', 1)
                word = word.strip().lower()
                translation = translation.strip().lower()
                
                if word and translation:
                    user_data[user_id].dictionary[word] = translation
                    words_count += 1
                    
        # Vaqtinchalik faylni o'chirish
        os.remove(temp_file)
        return words_count
        
    except Exception as e:
        logger.error(f"DOCX faylni qayta ishlashda xatolik: {e}")
        if os.path.exists(f"temp_{user_id}.docx"):
            os.remove(f"temp_{user_id}.docx")
        return 0

def process_pdf_file(file_content, user_id):
    """PDF faylni qayta ishlash"""
    try:
        # Vaqtinchalik fayl yaratish
        temp_file = f"temp_{user_id}.pdf"
        with open(temp_file, 'wb') as f:
            f.write(file_content)
            
        # PDF faylni o'qish
        pdf_reader = PyPDF2.PdfReader(temp_file)
        words_count = 0
        
        # Har bir sahifani o'qish
        for page in pdf_reader.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            for line in lines:
                if '-' in line:
                    word, translation = line.split('-', 1)
                    word = word.strip().lower()
                    translation = translation.strip().lower()
                    
                    if word and translation:
                        user_data[user_id].dictionary[word] = translation
                        words_count += 1
                        
        # Vaqtinchalik faylni o'chirish
        os.remove(temp_file)
        return words_count
        
    except Exception as e:
        logger.error(f"PDF faylni qayta ishlashda xatolik: {e}")
        if os.path.exists(f"temp_{user_id}.pdf"):
            os.remove(f"temp_{user_id}.pdf")
        return 0
# Quiz boshlanishi
def ask_question_count(message):
    try:
        user_id = message.from_user.id
        if len(user_data[user_id].dictionary) < 4:
            safe_send_message(
                message.chat.id,
                "❌ Quiz boshlash uchun kamida 4 ta so'z kiritilgan bo'lishi kerak!"
            )
            return
            
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("10 ta savol", "20 ta savol", "30 ta savol")
        
        safe_send_message(
            message.chat.id,
            "📝 Nechta savol tuzishni xohlaysiz?",
            markup
        )
    except Exception as e:
        logger.error(f"Savol sonini so'rashda xatolik: {e}")

@bot.message_handler(func=lambda message: message.text in ["10 ta savol", "20 ta savol", "30 ta savol"])
def start_quiz(message):
    try:
        user_id = message.from_user.id
        question_count = int(message.text.split()[0])
        
        if len(user_data[user_id].dictionary) < question_count:
            safe_send_message(
                message.chat.id,
                f"❌ Lug'atda yetarli so'z mavjud emas!\n"
                f"Mavjud so'zlar soni: {len(user_data[user_id].dictionary)}"
            )
            return
        
        # Quiz savollarini tayyorlash
        words = list(user_data[user_id].dictionary.items())
        selected_words = random.sample(words, question_count)
        
        user_data[user_id].current_quiz = []
        for word, translation in selected_words:
            # 50% ehtimol bilan so'z-tarjima yoki tarjima-so'z bo'ladi
            if random.choice([True, False]):
                question = f"'{word}' so'zining tarjimasi qaysi?"
                answer = translation
            else:
                question = f"'{translation}' so'zining tarjimasi qaysi?"
                answer = word
            
            # Noto'g'ri javoblarni tanlash
            other_words = [w for w in words if w != (word, translation)]
            wrong_answers = random.sample(
                [w[1] if answer == word else w[0] for w in other_words],
                3
            )
            
            options = wrong_answers + [answer]
            random.shuffle(options)
            
            user_data[user_id].current_quiz.append({
                'question': question,
                'options': options,
                'correct_answer': answer
            })
        
        user_data[user_id].current_question = 0
        user_data[user_id].score = 0
        user_data[user_id].quiz_start_time = time.time()
        
        show_question(message)
    except Exception as e:
        logger.error(f"Quiz boshlanishida xatolik: {e}")

def show_question(message):
    try:
        user_id = message.from_user.id
        state = user_data[user_id]
        
        if state.current_question >= len(state.current_quiz):
            show_results(message)
            return
        
        question = state.current_quiz[state.current_question]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Javoblarni 2x2 formatda joylashtirish
        options = list(question['options'])
        markup.row(options[0], options[1])
        markup.row(options[2], options[3])
        
        state.question_start_time = time.time()
        safe_send_message(
            message.chat.id,
            f"📝 Savol {state.current_question + 1}/{len(state.current_quiz)}:\n\n"
            f"{question['question']}\n\n"
            f"⏱ Vaqt: 10 soniya",
            markup
        )
    except Exception as e:
        logger.error(f"Savolni ko'rsatishda xatolik: {e}")

@bot.message_handler(func=lambda message: True)
def check_answer(message):
    try:
        user_id = message.from_user.id
        if user_id not in user_data:
            return
        
        state = user_data[user_id]
        if not state.current_quiz or state.current_question >= len(state.current_quiz):
            return
        
        current_time = time.time()
        time_spent = current_time - state.question_start_time
        
        current_question = state.current_quiz[state.current_question]
        
        if time_spent > 10:
            safe_send_message(message.chat.id, "⏱ Vaqt tugadi!")
        else:
            if message.text == current_question['correct_answer']:
                state.score += 1
                safe_send_message(message.chat.id, "✅ To'g'ri!")
            else:
                safe_send_message(
                    message.chat.id,
                    f"❌ Noto'g'ri!\n"
                    f"To'g'ri javob: {current_question['correct_answer']}"
                )
        
        state.current_question += 1
        show_question(message)
    except Exception as e:
        logger.error(f"Javobni tekshirishda xatolik: {e}")

def show_results(message):
    try:
        user_id = message.from_user.id
        state = user_data[user_id]
        
        total_time = time.time() - state.quiz_start_time
        total_questions = len(state.current_quiz)
        percentage = (state.score/total_questions)*100
        
        if percentage >= 80:
            grade = "🏆 A'lo"
        elif percentage >= 60:
            grade = "🎉 Yaxshi"
        elif percentage >= 40:
            grade = "👍 Qoniqarli"
        else:
            grade = "💪 Yaxshilash kerak"
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📝 So'zlarni kiritish", "📝 Ko'p so'z kiritish")
        markup.row("📁 File yuklash")
        
        result = (
            f"{grade}\n\n"
            f"✅ To'g'ri javoblar: {state.score}/{total_questions}\n"
            f"⏱ Umumiy vaqt: {int(total_time)} soniya\n"
            f"📊 Natija: {percentage:.1f}%"
        )
        
        safe_send_message(message.chat.id, result, markup)
        
        logger.info(
            f"Foydalanuvchi {user_id} - "
            f"Natija: {state.score}/{total_questions} "
            f"Vaqt: {int(total_time)}s "
            f"Foiz: {percentage:.1f}%"
        )
    except Exception as e:
        logger.error(f"Natijalarni ko'rsatishda xatolik: {e}")

if __name__ == "__main__":
    try:
        # Bot ma'lumotlarini olish
        me = bot.get_me()
        print(f"Bot ma'lumotlari - ID: {me.id}, Username: @{me.username}")
        logger.info(f"Bot ulandi - @{me.username}")
        
        # Botni ishga tushirish
        print("Bot ishga tushdi...")
        bot.polling(none_stop=True)
        
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        logger.error(f"Bot ishlashida xatolik: {e}")