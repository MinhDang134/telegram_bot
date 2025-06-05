import logging
import httpx
import asyncio
import signal
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Bot, Update
from telegram.request import HTTPXRequest

import config

# Cấu hình cơ bản
TOKEN = config.BOT_TOKEN # Sử dụng token thực tế của bạn
CHAT_ID = config.CHAT_ID  # Sử dụng chat ID thực tế của bạn

# Cấu hình proxy
PROXY_LOGIN = config.PROXY_LOGIN
PROXY_PASSWORD = config.PROXY_PASSWORD
PROXY_IP_HTTP = config.PROXY_IP_HTTP
PROXY_PORT_HTTP = config.PROXY_PORT_HTTP
PROXY_URL = f'socks5://{PROXY_LOGIN}:{PROXY_PASSWORD}@{PROXY_IP_HTTP}:{PROXY_PORT_HTTP}'
VERIFY_SSL = True

# Cấu hình logging chi tiết hơn
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Thay đổi từ INFO thành DEBUG để xem nhiều thông tin hơn
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def kiem_tra_proxy(proxy_url_can_kiem_tra, xac_minh_ssl=True):
    """Kiểm tra xem proxy có hoạt động không"""
    if not proxy_url_can_kiem_tra:
        logger.info("Không có PROXY_URL được định nghĩa, bỏ qua kiểm tra proxy.")
        return False
    logger.info(f"Đang kiểm tra proxy: {proxy_url_can_kiem_tra}")
    try:
        async with httpx.AsyncClient(proxies=proxy_url_can_kiem_tra, verify=xac_minh_ssl, timeout=20.0) as client:
            response = await client.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
            logger.info(f"Kết quả kiểm tra proxy: Trạng thái {response.status_code}")
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"Thông tin bot: @{bot_info.get('result', {}).get('username', 'N/A')}")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra proxy: {type(e).__name__} - {e}")
    return False


# Hàm xử lý tất cả tin nhắn để debug
async def xu_ly_tat_ca_tin_nhan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tất cả tin nhắn để debug"""
    logger.info("=" * 50)
    logger.info("NHẬN ĐƯỢC TIN NHẮN MỚI!")
    logger.info(f"Từ người dùng: {update.effective_user.id} (@{update.effective_user.username})")
    logger.info(f"Tên người dùng: {update.effective_user.first_name} {update.effective_user.last_name or ''}")
    logger.info(f"Chat ID: {update.effective_chat.id}")
    logger.info(f"Loại chat: {update.effective_chat.type}")
    logger.info(f"Nội dung tin nhắn: '{update.message.text if update.message.text else 'N/A'}'")
    logger.info("=" * 50)


async def bat_dau(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    logger.info("🚀 LỆNH /START ĐÃ ĐƯỢC GỌI!")
    logger.info(f"User ID: {update.effective_user.id}")
    logger.info(f"Chat ID: {update.effective_chat.id}")
    logger.info(f"Username: @{update.effective_user.username}")


    try:
        # Thử gửi tin nhắn
        tin_nhan_gui = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 Xin chào! Bot đã sẵn sàng hoạt động!\n\n"
                 f"👤 Tên bạn: {update.effective_user.first_name}\n"
                 f"🆔 User ID: {update.effective_user.id}\n"
                 f"💬 Chat ID: {update.effective_chat.id}"
        )
        logger.info(f"✅ ĐÃ GỬI THÀNH CÔNG tin nhắn ID: {tin_nhan_gui.message_id}")

    except Exception as e:
        logger.error(f"❌ LỖI khi gửi tin nhắn /start: {type(e).__name__} - {e}", exc_info=True)


async def phan_hoi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Phản hồi lại tin nhắn của người dùng"""
    logger.info(f"📝 Phản hồi tin nhắn: '{update.message.text}'")
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📣 Bạn vừa nói: '{update.message.text}'"
        )
        logger.info("✅ Đã phản hồi thành công")
    except Exception as e:
        logger.error(f"❌ Lỗi khi phản hồi: {e}", exc_info=True)


async def main() -> None:
    """Hàm chính - chạy bot Telegram"""
    logger.info("🔄 BẮT ĐẦU KHỞI ĐỘNG BOT...")
    logger.info(f"Proxy: {PROXY_URL if PROXY_URL else 'Không có proxy'}")

    # Kiểm tra proxy
    proxy_hoat_dong = await kiem_tra_proxy(PROXY_URL, xac_minh_ssl=VERIFY_SSL)

    xu_ly_request_ptb = None
    if proxy_hoat_dong:
        logger.info(f"✅ Proxy hoạt động tốt: {PROXY_URL}")
        try:
            xu_ly_request_ptb = HTTPXRequest(
                proxy=PROXY_URL,
                connect_timeout=100.0,
                read_timeout=100.0,
                write_timeout=100.0,
                pool_timeout=100.0
            )
            logger.info("✅ Đã tạo HTTPXRequest với proxy")
        except Exception as e:
            logger.error(f"❌ Lỗi tạo HTTPXRequest: {e}")
            xu_ly_request_ptb = None
    else:
        logger.warning("⚠️ Proxy không hoạt động, chạy không proxy")

    # Xây dựng ứng dụng
    builder_ung_dung = Application.builder()
    if xu_ly_request_ptb:
        ung_dung = builder_ung_dung.token(TOKEN).request(xu_ly_request_ptb).build()
        logger.info("✅ Bot được cấu hình với proxy")
    else:
        ung_dung = builder_ung_dung.token(TOKEN).build()
        logger.info("✅ Bot được cấu hình không proxy")

    # Thêm handler để debug tất cả tin nhắn
    ung_dung.add_handler(MessageHandler(filters.ALL, xu_ly_tat_ca_tin_nhan), group=-1)

    # Thêm các handler chính
    ung_dung.add_handler(CommandHandler("start", bat_dau))
    ung_dung.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, phan_hoi))

    logger.info("✅ Đã thêm tất cả handlers")

    # Khởi chạy bot
    logger.info("🚀 ĐANG KHỞI CHẠY BOT...")
    try:
        await ung_dung.initialize()
        logger.info("✅ Đã initialize")

        await ung_dung.start()
        logger.info("✅ Đã start application")

        # Kiểm tra thông tin bot
        try:
            bot_info = await ung_dung.bot.get_me()
            logger.info(f"🤖 Bot Info: @{bot_info.username} (ID: {bot_info.id})")
            logger.info(f"📛 Tên bot: {bot_info.first_name}")
        except Exception as e:
            logger.error(f"❌ Không thể lấy thông tin bot: {e}")

        await ung_dung.updater.start_polling(
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True  # Bỏ qua tin nhắn cũ
        )

        logger.info("🎉 BOT ĐÃ SẴN SÀNG! Gửi /start để test")
        logger.info("⏹️  Nhấn Ctrl+C để dừng bot")

        # Giữ bot chạy
        su_kien_dung = asyncio.Event()

        def xu_ly_tin_hieu(so_tin_hieu, khung):
            logger.info("🛑 Nhận tín hiệu dừng...")
            su_kien_dung.set()

        signal.signal(signal.SIGINT, xu_ly_tin_hieu)
        signal.signal(signal.SIGTERM, xu_ly_tin_hieu)

        await su_kien_dung.wait()

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng: {e}", exc_info=True)
    finally:
        logger.info("🔄 Đang tắt bot...")
        try:
            await ung_dung.updater.stop()
            await ung_dung.stop()
            await ung_dung.shutdown()
            logger.info("✅ Bot đã tắt hoàn toàn")
        except Exception as e:
            logger.error(f"❌ Lỗi khi tắt: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot dừng bởi người dùng (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Lỗi nghiêm trọng: {type(e).__name__} - {e}", exc_info=True)