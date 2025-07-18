import os
from pathlib import Path


def parse_quiz_file(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file:
        content = file.read()

    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]

    questions = {}
    current_question = None

    for block in blocks:
        if not (block.startswith('Вопрос') or block.startswith('Ответ')):
            continue

        if block.startswith('Вопрос'):
            current_question = block.split(':', 1)[1].strip()
            continue

        if not current_question:
            continue

    return questions


def load_all_questions(questions_dir=None):
    all_questions = {}
    base_dir = Path(questions_dir or os.getenv('QUESTIONS_DIR', './quiz-questions'))

    for filename in os.listdir(base_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(base_dir, filename)
            all_questions.update(parse_quiz_file(file_path))

    return all_questions