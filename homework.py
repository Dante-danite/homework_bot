"""Модуль для телеграм-бота, проверяющего статус заданий."""

import logging
import json
import os
import sys
from http import HTTPStatus
import requests
import time

from dotenv import load_dotenv
import telegram

import exceptions


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(stream=sys.stdout)]
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
TWO_WEEKS = 1209600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов в окружении."""
    all_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN
    }
    missing_tokens = []
    for key, value in all_tokens.items():
        if not value:
            missing_tokens.append(key)
    result = not missing_tokens
    return missing_tokens, result


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Сообщение "{message}" успешно отправлено.')
    except Exception as error:
        raise error


def get_api_answer(timestamp):
    """Запрос к API Яндекс.Практикума."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={
                'from_date': timestamp
            }
        )
    except requests.RequestException as error:
        logging.error(f'Ошибка запроса к API: {error}')
    if response.status_code == HTTPStatus.OK:
        try:
            return response.json()
        except json.decoder.JSONDecodeError as error:
            raise error
    raise exceptions.APINotAvailableError(response.status_code)


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не содержит словаря')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Объект homeworks в ответе от API - не список.')
    current_date = response.get('current_date')
    if not isinstance(current_date, int):
        raise TypeError('Объект current_date в ответе API - не целое число.')
    return homework


def parse_status(homework):
    """Создание сообщения для бота."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('В словаре homeworks нет ключа homework_name.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        raise exceptions.StatusError(status)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Телеграм-бот для проверки домашней работы.

    Проверяет наличие токенов в окружении, запрашивает
    последние данные о статусе домашней работы у Яндекс.Практикума
    и передает сообщение об изменении статуса работы.
    """
    tokens_check, missing_tokens = check_tokens()
    if not tokens_check:
        logging.critical(f'Ошибка доступа к токенам: {missing_tokens}')
        raise exceptions.TokenNotFoundError

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - TWO_WEEKS
    last_error = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks_list = check_response(response)
            if homeworks_list:
                message = parse_status(homeworks_list[0])
                send_message(bot, message)
            else:
                message = 'Статус работы не изменился'
                logging.debug(message)
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            logging.error(error)
            if error != last_error:
                send_message(bot, error)
            last_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
