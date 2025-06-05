# error_handler.py

import logging
import requests
import traceback
import config


class TelegramLogHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)


        if record.exc_info:
            log_entry += "\n\n" + "".join(traceback.format_exception(*record.exc_info))


        if len(log_entry) > 4000:
            log_entry = log_entry[:4000] + "\n... (nội dung đã được rút gọn)"

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': f"‼️ **Lỗi từ Bot** ‼️\n\n<pre>{log_entry}</pre>",
            'parse_mode': 'HTML'
        }

        try:
            requests.post(url, data=payload, timeout=10)
        except Exception:
            pass