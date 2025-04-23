import os
import requests
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# 从环境变量获取 Token 和 Pinata 密钥
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
IPFS_API_KEY        = os.getenv("IPFS_API_KEY")
IPFS_API_SECRET     = os.getenv("IPFS_API_SECRET")
IPFS_API_URL        = "https://api.pinata.cloud/pinning/pinFileToIPFS"

# 存储每个用户上传的 IPFS 链接
_user_links = defaultdict(list)

def upload_to_ipfs(image_path: str) -> str | None:
    headers = {
        "pinata_api_key": IPFS_API_KEY,
        "pinata_secret_api_key": IPFS_API_SECRET,
    }
    with open(image_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(IPFS_API_URL, headers=headers, files=files)
    if resp.status_code == 200:
        cid = resp.json()["IpfsHash"]
        return f"https://ipfs.io/ipfs/{cid}"
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 欢迎使用 IPFS 图片上传 Bot！\n\n"
        "• 直接发送图片给我，自动上传到 IPFS 并返回链接。\n"
        "• 使用 /clear 清除你所有的上传记录。"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = await update.message.photo[-1].get_file()
    path = f"/tmp/{user_id}_{update.message.message_id}.jpg"
    await photo.download_to_drive(path)

    link = upload_to_ipfs(path)
    os.remove(path)

    if link:
        _user_links[user_id].append(link)
        # 发送带按钮的链接提示
        keyboard = [[InlineKeyboardButton("🔗 点击访问图片", url=link)]]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("上传成功！点击下方按钮或复制链接：", reply_markup=markup)
        await update.message.reply_text(link)
    else:
        await update.message.reply_text("❌ 上传失败，请稍后重试。")

async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in _user_links and _user_links[user_id]:
        _user_links.pop(user_id)
        await update.message.reply_text("✅ 已清除你的所有上传记录。")
    else:
        await update.message.reply_text("ℹ️ 你还没有任何上传记录，无需清除。")

def main():
    app = Application.builder().token(TELEGRAM_API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_data))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
