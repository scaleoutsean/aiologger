import json
import logging
import traceback
from datetime import datetime
from inspect import istraceback
from typing import Callable, Any


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
LOGGED_AT_FIELDNAME = 'logged_at'
LINE_NUMBER_FIELDNAME = 'line_number'
FUNCTION_NAME_FIELDNAME = 'function'
LOG_LEVEL_FIELDNAME = 'level'
MSG_FIELDNAME = 'msg'
FILE_PATH_FIELDNAME = 'file_path'


class JsonFormatter(logging.Formatter):
    def __init__(self,
                 serializer: Callable[..., str] = json.dumps,
                 default_msg_fieldname: str = None,
                 datetime_format: str = None):
        super(JsonFormatter, self).__init__()
        self.serializer = serializer

        self.default_msg_fieldname = default_msg_fieldname or MSG_FIELDNAME
        self.datetime_format = datetime_format or DATETIME_FORMAT

    def _default_handler(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(self.datetime_format)
        elif istraceback(obj):
            tb = ''.join(traceback.format_tb(obj))
            return tb.strip().split('\n')
        elif isinstance(obj, Exception):
            return "Exception: %s" % repr(obj)
        elif callable(obj):
            return obj()
        return str(obj)

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a record and serializes it as a JSON str. If record message isnt
        already a dict, initializes a new dict and uses `default_msg_fieldname`
        as a key as the record msg as the value.
        """
        msg = record.msg
        if not isinstance(record.msg, dict):
            msg = {self.default_msg_fieldname: msg}

        if record.exc_info:
            msg['exc_info'] = record.exc_info
        if record.exc_text:
            msg['exc_text'] = record.exc_text

        return self.serializer(msg, default=self._default_handler)


class ExtendedJsonFormatter(JsonFormatter):
    level_to_name_mapping = logging._levelToName
    default_fields = frozenset([
        LOG_LEVEL_FIELDNAME,
        LOGGED_AT_FIELDNAME,
        LINE_NUMBER_FIELDNAME,
        FUNCTION_NAME_FIELDNAME,
        FILE_PATH_FIELDNAME
    ])

    def __init__(self,
                 serializer: Callable[..., str] = json.dumps,
                 default_msg_fieldname: str = None,
                 datetime_format: str = None,
                 exclude_fields=None):
        """
        :type serializer: Callable[[Dict], str]
        :type exclude_fields: Iterable[str]
        """
        super(ExtendedJsonFormatter, self).__init__(
            serializer=serializer,
            default_msg_fieldname=default_msg_fieldname,
            datetime_format=datetime_format
        )
        if exclude_fields is None:
            self.log_fields = self.default_fields
        else:
            self.log_fields = self.default_fields - set(exclude_fields)

    def formatter_fields_for_record(self, record):
        """
        :type record: aiologger.loggers.json.LogRecord
        """
        default_fields = (
            (LOGGED_AT_FIELDNAME, datetime.now().strftime(DATETIME_FORMAT)),
            (LINE_NUMBER_FIELDNAME, record.lineno),
            (FUNCTION_NAME_FIELDNAME, record.funcName),
            (LOG_LEVEL_FIELDNAME, self.level_to_name_mapping[record.levelno]),
            (FILE_PATH_FIELDNAME, record.pathname)
        )

        for field, value in default_fields:
            if field in self.log_fields:
                yield field, value

    def format(self, record) -> str:
        """
        :type record: aiologger.loggers.json.LogRecord
        """
        msg = dict(self.formatter_fields_for_record(record))
        if record.flatten and isinstance(record.msg, dict):
            msg.update(record.msg)
        else:
            msg[MSG_FIELDNAME] = record.msg

        if record.extra:
            msg.update(record.extra)
        if record.exc_info:
            msg['exc_info'] = record.exc_info
        if record.exc_text:
            msg['exc_text'] = record.exc_text

        return self.serializer(msg,
                               default=self._default_handler,
                               **record.serializer_kwargs)
