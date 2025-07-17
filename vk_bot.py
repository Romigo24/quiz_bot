import os
import random
import logging

import redis
from dotenv import load_dotenv
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from quiz_questions_loader import load_all_questions


logger = logging.getLogger(__file__)


def create_bot_functions(vk_api_client, redis_connect, questions):
    def create_keyboard():
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
        return keyboard.get_keyboard()

    def send_message(user_id: int, text: str):
        vk_api_client.messages.send(
            user_id=user_id,
            message=text,
            keyboard=create_keyboard(),
            random_id=random.randint(1, 10000)
        )

    def handle_new_question(user_id):
        question = random.choice(list(questions.keys()))
        redis_connect.set(f'vk-quiz:{user_id}:current_question', question)
        send_message(user_id, f'Вопрос:\n{question}')

    def handle_give_up(user_id):
        question = redis_connect.get(f'vk-quiz:{user_id}:current_question')
        if question:
            answer = questions[question]
            send_message(user_id, f'Правильный ответ:\n{answer}')
            handle_new_question(user_id)

    def handle_score(user_id):
        score = redis_connect.get(f'vk-quiz:{user_id}:score') or '0'
        send_message(user_id, f'Ваш текущий счёт: {score}')

    def handle_answer(user_id, text):
        question = redis_connect.get(f'vk-quiz:{user_id}:current_question')
        if not question:
            send_message(user_id, 'Нажмите "Новый вопрос" чтобы начать')
            return
        
        correct_answer = questions[question]
        if text.lower() == correct_answer.lower():
            redis_connect.incr(f'vk-quiz:{user_id}:score')
            send_message(user_id, 'Правильно! +1 балл')
            handle_new_question(user_id)
        else:
            send_message(user_id, 'Неправильно. Попробуйте ещё раз')

    return {
        'send_message': send_message,
        'handle_new_question': handle_new_question,
        'handle_give_up': handle_give_up,
        'handle_score': handle_score,
        'handle_answer': handle_answer
    }


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

        handlers = create_bot_functions(vk, redis_connect, questions)

        logger.info("Бот-викторина запущен...")
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                text = event.text
                
                if text == 'Новый вопрос':
                    handlers['handle_new_question'](user_id)
                elif text == 'Сдаться':
                    handlers['handle_give_up'](user_id)
                elif text == 'Мой счёт':
                    handlers['handle_score'](user_id)
                else:
                    handlers['handle_answer'](user_id, text)

    except Exception as e:
        logger.exception(f"Ошибка в работе бота: {e}")


if __name__ == '__main__':
    main()