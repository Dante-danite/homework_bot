class TelegramSendErrorException(Exception):
    """Исключение отправки сообщения в телеграм"""
    pass


class NotExistKeyException(KeyError):
    """Исключение из за несуществующего ключа"""
    pass


class NotExistTypeException(TypeError):
    """Исключение из за несуществующего типа"""
    pass


class ApiRequestException(Exception):
    """Исключение из-за ошибки GET-запроса к эндпоинту."""
    pass


class TokenNotFoundException(Exception):
    """Исключение из-за отсутствия токена"""
    pass


class UnExpectedResponseException(Exception):
    """Исключение из-за неожидаемого ответа"""
    pass
