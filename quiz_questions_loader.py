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
    for file_path in questions_dir.glob('*.txt'):
        all_questions.update(parse_quiz_file(file_path))

    return all_questions