import os
import random
import logging

import redis
from dotenv import load_dotenv
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from quiz_questions_loader import load_all_questions


logger = logging.getLogger(__name__)


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def send_message(vk_api_client, user_id, text):
    vk_api_client.messages.send(
        user_id=user_id,
        message=text,
        keyboard=create_keyboard(),
        random_id=random.randint(1, 10000)
    )


def handle_new_question(vk_api_client, redis_connect, questions, user_id):
    question = random.choice(list(questions.keys()))
    redis_connect.set(f'vk-quiz:{user_id}:current_question', question)
    send_message(vk_api_client, user_id, f'Вопрос:\n{question}')


def handle_give_up(vk_api_client, redis_connect, questions, user_id):
    question = redis_connect.get(f'vk-quiz:{user_id}:current_question')
    if question:
        answer = questions[question]
        send_message(vk_api_client, user_id, f'Правильный ответ:\n{answer}')
        handle_new_question(vk_api_client, redis_connect, questions, user_id)


def handle_score(vk_api_client, redis_connect, user_id):
    score = redis_connect.get(f'vk-quiz:{user_id}:score') or '0'
    send_message(vk_api_client, user_id, f'Ваш текущий счёт: {score}')


def handle_answer(vk_api_client, redis_connect, questions, user_id, text):
    question = redis_connect.get(f'vk-quiz:{user_id}:current_question')
    if not question:
        send_message(vk_api_client, user_id, 'Нажмите "Новый вопрос" чтобы начать')
        return

    correct_answer = questions[question]
    if text.lower() == correct_answer.lower():
        redis_connect.incr(f'vk-quiz:{user_id}:score')
        send_message(vk_api_client, user_id, 'Правильно! +1 балл')
        handle_new_question(vk_api_client, redis_connect, questions, user_id)
    else:
        send_message(vk_api_client, user_id, 'Неправильно. Попробуйте ещё раз')


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    try:
        load_dotenv()
        questions = load_all_questions()
        if not questions:
            logger.error("Не загружено ни одного вопроса!")
            return

        redis_connect = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT')),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True
        )
        redis_connect.ping()

        vk_session = vk_api.VkApi(token=os.environ['VK_BOT_TOKEN'])
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        logger.info("Бот-викторина запущен...")
        # for event in longpoll.listen():
        #     if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        #         user_id = event.user_id
        #         text = event.text
                
        #         if text.lower() in ('начать', 'start'):
        #             send_message(vk, user_id, 'Привет! Я бот для викторины. Нажми "Новый вопрос" чтобы начать.')
        #         elif text == 'Новый вопрос':
        #             handle_new_question(vk, redis_connect, questions, user_id)
        #         elif text == 'Сдаться':
        #             handle_give_up(vk, redis_connect, questions, user_id)
        #         elif text == 'Мой счёт':
        #             handle_score(vk, redis_connect, user_id)
        #         else:
        #             handle_answer(vk, redis_connect, questions, user_id, text)
        for event in longpoll.listen():
            if not (event.type == VkEventType.MESSAGE_NEW and event.to_me):
                continue

            user_id = event.user_id
            text = event.text.lower()

            if text in ['начать', 'start']:
                send_message(vk, user_id, 'Привет! Я бот для викторины. Нажми "Новый вопрос" чтобы начать.')
                continue

            if text == 'новый вопрос':
                handle_new_question(vk, redis_connect, questions, user_id)
                continue

            if text == 'сдаться':
                handle_give_up(vk, redis_connect, questions, user_id)
                continue

            if text == 'мой счёт':
                handle_score(vk, redis_connect, user_id)
                continue

            handle_answer(vk, redis_connect, questions, user_id, text)

    except Exception as e:
        logger.exception(f"Ошибка в работе бота: {e}")

if __name__ == '__main__':
    main()