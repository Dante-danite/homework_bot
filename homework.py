import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы."""
    tokens = ['TELEGRAM_TOKEN', 'PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID']
    for token in tokens:
        if not globals()[token]:
            raise exceptions.TokenNotFoundException(
                f'{token} отсутствует')


def send_message(bot: telegram.Bot, message):
    """Oтправляет сообщение в Telegram чат."""
    try:
        logging.debug(f'Начало отправки сообщения {message}')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Вам отправлено сообщение! {message}')
    except TelegramError as error:
        message = f'Не удалось отправить сообщение {error}'
        logging.error(message)
        exceptions.TelegramSendErrorException(message)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        params = {'from_date': timestamp}
        logging.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
        homework = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise exceptions.ApiRequestException('Исключение из-за ошибки'
                                             ' GET-запроса к эндпоинту')
    homework_json = homework.json()
    logging.info(f'Получен ответ {homework_json}')
    if homework.status_code != HTTPStatus.OK:
        raise exceptions.UnExpectedResponseException(homework_json)
    return homework_json


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not isinstance(response, dict):
        raise exceptions.NotExistTypeException('Ошибка в типе данных.')

    if 'current_date' not in response:
        raise exceptions.NotExistKeyException(
            'Ошибка словаря по ключу "current_date".')

    if 'homeworks' not in response:
        raise exceptions.NotExistKeyException(
            'Ошибка словаря по ключу "homeworks".')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise exceptions.NotExistTypeException(
            'Homeworks не является списком.')

    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе, статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not homework_name:
        raise exceptions.NotExistKeyException(
            'Нет значения под ключем homework_name в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.NotExistKeyException(
            'Нет ключа homework_status в ответе API')
    if 'status' not in homework:
        raise exceptions.NotExistKeyException(
            'Ключа "status" нет в словаре')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except exceptions.TokenNotFoundException as error:
        logging.critical(error)
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = None
    message_error = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            logging.info(f'homeworks {homeworks}')
            if not homeworks:
                message = 'Список homeworks пустой'
            else:
                message = parse_status(homeworks[0])
                logging.info(f'homework {message}\n')
            if message != last_status:
                send_message(bot, message)
                last_status = message
            logging.info(f'\n timestamp {timestamp} \n')
            timestamp = response.get('current_date')

        except exceptions.TelegramSendErrorException as error:
            logging.error(error)
        except Exception as error:
            message_error = f"Сбой в работе программы: {error}"
            logging.error(message_error)
            try:
                send_message(bot, message_error)
            except exceptions.TelegramSendErrorException as error:
                logging.error(error)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)s - %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    main()
