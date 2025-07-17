import os
import random
import logging

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)

from quiz_questions_loader import load_all_questions


logger = logging.getLogger(__file__)


NEW_QUESTION, ANSWER_ATTEMPT = range(2)


def start(update, context):
    questions = context.bot_data['questions']
    buttons = [['Новый вопрос', 'Сдаться'], ['Мой счёт']]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    if not questions:
        update.message.reply_text(
            "Ошибка: вопросы не найдены!",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    update.message.reply_text(
        'Привет! Я бот для викторин! Нажми "Новый вопрос" чтобы начать.',
        reply_markup=reply_markup
    )
    return NEW_QUESTION


def handle_new_question_request(update, context):
    questions = context.bot_data['questions']
    redis_connect = context.bot_data['redis']
    user_id = update.message.from_user.id
    question = random.choice(list(questions.keys()))
    redis_connect.set(f'tg-quiz:{user_id}:current_question', question)
    update.message.reply_text(f'Вопрос:\n{question}')
    return ANSWER_ATTEMPT


def handle_solution_attempt(update, context):
    questions = context.bot_data['questions']
    redis_connect = context.bot_data['redis']
    user_id = update.message.from_user.id
    user_message = update.message.text

    if user_message == 'Сдаться':
        return handle_give_up(update, context)
    elif user_message == 'Мой счёт':
        return handle_show_score(update, context)

    question = redis_connect.get(f'tg-quiz:{user_id}:current_question')
    if question:
        correct_answer = questions[question]
        if user_message.lower() == correct_answer.lower():
            redis_connect.incr(f'tg-quiz:{user_id}:score')
            update.message.reply_text('Правильно! +1 балл\nНажми "Новый вопрос" для продолжения')
            return NEW_QUESTION
        else:
            update.message.reply_text('Неправильно. Попробуйте ещё раз')
            return ANSWER_ATTEMPT
    else:
        update.message.reply_text('Нажмите "Новый вопрос" чтобы начать')
        return NEW_QUESTION


def handle_give_up(update, context):
    questions = context.bot_data['questions']
    redis_connect = context.bot_data['redis']
    user_id = update.message.from_user.id
    current_question = redis_connect.get(f'tg-quiz:{user_id}:current_question')
    if current_question:
        answer = questions[current_question]
        update.message.reply_text(f'Правильный ответ:\n{answer}')
        redis_connect.delete(f'tg-quiz:{user_id}:current_question')
    return handle_new_question_request(update, context)

def handle_show_score(update, context):
    redis_connect = context.bot_data['redis']
    user_id = update.message.from_user.id
    score = redis_connect.get(f'tg-quiz:{user_id}:score') or 0
    update.message.reply_text(f'Ваш текущий счёт: {score}\nПродолжайте играть!')
    return ANSWER_ATTEMPT


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.ERROR
    )
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        redis_connect = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        password=os.getenv('REDIS_PASSWORD'),
        decode_responses=True
        )
        redis_connect.ping()

        tg_bot_token = os.environ['TG_BOT_TOKEN']
    except Exception:
        logger.exception('Ошибка при иницииализации окужения или подключения к Redis:')
        return

    try:
        all_questions = load_all_questions()

        if not all_questions:
            logger.warning("Не загружено ни одного вопроса.")
    except Exception:
        logger.exception("Ошибка при чтении вопросов: {e}")
        return

    try:
        updater = Updater(tg_bot_token)
        dp = updater.dispatcher
        dp.bot_data['questions'] = all_questions
        dp.bot_data['redis'] = redis_connect

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                NEW_QUESTION: [
                    MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request)
                ],
                ANSWER_ATTEMPT: [
                    MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt)
                ]
            },
            fallbacks=[]
        )

        dp.add_handler(conv_handler)
        updater.start_polling()
        updater.idle()
    except Exception:
        logger.exception('Ошибка при запуске бота: {e}')

if __name__ == '__main__':
    main()