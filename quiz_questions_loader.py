import os


def parse_quiz_file(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file:
        content = file.read()

    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]

    questions = {}
    current_question = None

    for block in blocks:
        if block.startswith('Вопрос'):
            current_question = block.split(':', 1)[1].strip()
        elif block.startswith('Ответ'):
            if current_question:
                answer = block.split(':', 1)[1].strip()
                questions[current_question] = answer

    return questions


def load_all_questions():
    all_questions = {}
    questions_dir = './quiz-questions'

    for filename in os.listdir(questions_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(questions_dir, filename)
            all_questions.update(parse_quiz_file(file_path))

    return all_questions