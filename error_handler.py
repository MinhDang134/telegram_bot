# error_handler.py

import logging
import traceback
import asyncio
import httpx  # <-- Dùng httpx thay cho requests
import config  # <-- Import config để lấy cấu hình proxy


class TelegramLogHandler(logging.Handler):
    """
    Một logging handler được tối ưu hóa để gửi log lỗi một cách bất đồng bộ,
    không làm chặn luồng chính của bot.
    """

    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        """
        Phương thức này vẫn là synchronous (đồng bộ), nhưng nó sẽ "lên lịch" cho một
        tác vụ bất đồng bộ chạy trong nền thay vì tự mình thực hiện việc gửi tin.
        """
        # Lấy vòng lặp sự kiện đang chạy của bot
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        # Nếu có vòng lặp sự kiện đang chạy, hãy tạo một tác vụ nền
        if loop and loop.is_running():
            log_entry = self.format(record)
            if record.exc_info:
                log_entry += "\n\n" + "".join(traceback.format_exception(*record.exc_info))

            # Giao việc gửi tin nhắn cho một tác vụ chạy nền, không cần chờ nó xong
            loop.create_task(self._send_message_async(log_entry))

    async def _send_message_async(self, log_entry: str):
        """
        Hàm bất đồng bộ này mới thực sự thực hiện việc gửi tin nhắn bằng httpx.
        """
        # Rút gọn tin nhắn nếu quá dài
        if len(log_entry) > 4000:
            log_entry = log_entry[:4000] + "\n... (nội dung đã được rút gọn)"

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': f"‼️ **Lỗi từ Bot** ‼️\n\n<pre>{log_entry}</pre>",
            'parse_mode': 'HTML'
        }

        # Tự động sử dụng proxy từ file config nếu có
        proxy_url = config.PROXY_URL if hasattr(config, 'PROXY_URL') and config.PROXY_URL else None

        try:
            # Dùng httpx.AsyncClient để gửi request bất đồng bộ
            async with httpx.AsyncClient(proxy=proxy_url) as client:
                await client.post(url, data=payload, timeout=10)
        except Exception as e:
            # Nếu việc gửi đi bị lỗi, in ra log để debug
            # Sử dụng logger gốc để tránh vòng lặp lỗi
            logging.getLogger(__name__).error(f"Lỗi khi gửi thông báo lỗi bất đồng bộ: {e}")