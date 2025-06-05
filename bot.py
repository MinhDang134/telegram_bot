# bot.py

import logging
import asyncio
import signal
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

import config
from error_handler import TelegramLogHandler

# --- Cấu hình logging giữ nguyên ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("telegram.ext").setLevel(logging.DEBUG)
logging.getLogger("telegram.bot").setLevel(logging.DEBUG)
print("--- CHẾ ĐỘ LOG CHI TIẾT ĐÃ ĐƯỢC BẬT ---")

telegram_handler = TelegramLogHandler(token=config.BOT_TOKEN, chat_id=config.CHAT_ID)
telegram_handler.setLevel(logging.ERROR)
logging.getLogger().addHandler(telegram_handler)
logger.info("✅ Bộ xử lý lỗi qua Telegram đã được kích hoạt.")



def tinh_trung_binh_cong(danh_sach_so: list) -> float:
    logger.info(f"Đang tính trung bình cho danh sách: {danh_sach_so}")
    return sum(danh_sach_so) / len(danh_sach_so)


async def tinh_toan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} đã gọi lệnh /tinh_toan.")
    danh_sach_dau_vao = []
    trung_binh = tinh_trung_binh_cong(danh_sach_dau_vao)
    await update.message.reply_text(f"Kết quả trung bình là: {trung_binh}")



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Lệnh /start từ user {update.effective_user.id}")
    await update.message.reply_text("Xin chào! Bot đã sẵn sàng.")

async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Phản hồi tin nhắn từ user {update.effective_user.id}")
    await update.message.reply_text(f"Bạn đã nói: {update.message.text}")

async def error_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} yêu cầu tạo lỗi thử nghiệm.")
    try:
        result = 1 / 0
    except Exception as e:
        logger.exception("Đây là một lỗi thử nghiệm được tạo ra có chủ đích.")
        await update.message.reply_text("🐞 Đã tạo lỗi thử nghiệm. Kiểm tra Telegram của admin nhé!")


# --- Hàm main đã được sửa lại ---
async def main() -> None:
    logger.info("Bắt đầu khởi động bot...")

    # 1. Tạo đối tượng request với đầy đủ cấu hình proxy và timeout
    request_handler = None
    if config.PROXY_URL:
        logger.info(f"Sử dụng proxy: {config.PROXY_URL}")
        request_handler = HTTPXRequest(
            proxy=config.PROXY_URL,
            connect_timeout=30.0,
            read_timeout=30.0,
            pool_timeout=60.0
        )

    # 2. TẠO một đối tượng Bot với token và cấu hình request đó
    configured_bot = Bot(token=config.BOT_TOKEN, request=request_handler)

    # 3. BUILD ứng dụng từ đối tượng Bot đã được cấu hình sẵn
    application = Application.builder().bot(configured_bot).build()

    # --- Phần còn lại của hàm main giữ nguyên ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("test_error", error_test_command))
    application.add_handler(CommandHandler("tinh_toan", tinh_toan_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
    application.add_error_handler(lambda u, c: logger.error("Lỗi từ PTB:", exc_info=c.error))

    try:
        await application.initialize()
        await application.updater.start_polling(drop_pending_updates=True) # Thêm drop_pending_updates cho chắc chắn
        await application.start()
        logger.info("🎉 Bot đã chạy thành công! Nhấn Ctrl+C để dừng.")

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)

        await stop_event.wait()
    except Exception as e:
        logger.critical("Lỗi không xác định trong hàm main.", exc_info=e)
    finally:
        logger.info("Bắt đầu quá trình tắt bot...")
        if application.updater and application.updater.is_running():
            await application.updater.stop()
        if application.running:
            await application.stop()
        await application.shutdown()
        logger.info("✅ Bot đã tắt hoàn toàn.")

if __name__ == '__main__':
    asyncio.run(main())