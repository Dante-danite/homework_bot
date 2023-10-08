"""Кастомизированные ошибки для модуля homework."""


class TokenNotFoundError(Exception):
    """Ошибка доступа к токенам в окружении."""

    def __init__(self):
        super().__init__('Критическая ошибка окружения.')


class APINotAvailableError(Exception):
    """Ошибка доступа к API."""

    def __init__(self, status):
        super().__init__(f'Ошибка доступа к API. Статус ошибки: {status}')


class StatusError(Exception):
    """Ошибка статуса в объекте homework."""

    def __init__(self, status):
        super().__init__('Непредусмотренный статус поля'
                         f' status в объекте homework: {status}')