from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram._update import Update
from configuration import Config

config = Config('configuration.yaml')
subs = config.get_db().subscriptions
clients = config.get_db().clients


async def start(update: Update, context):
    """Sends a message with three inline buttons attached."""

    keyboard = [
        [InlineKeyboardButton("دریافت اشتراک تست", callback_data="test")],
    ]
    if update.message.from_user.id == config.admin:
        keyboard.append([
            InlineKeyboardButton("پنل ادمین", callback_data="admin")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("به ربات تستی ما خوش اومدی حالا خدافظ", reply_markup=reply_markup)


async def remaining(update: Update, context):
    if update.message.from_user.id != config.admin:
        return

    total = 0
    remaining_total = 0
    total_sale = 0
    for client in clients.find({}):
        sub = subs.find_one({'_id': client['subscription']})
        total += client['usage']
        remaining_total += sub['traffic'] - client['usage']
        total_sale += sub['traffic']

    txt = f"""
    💡 کل حجم مصرفی مشتریان تا اینجا {total} هست.

💡 کل حجم باقی مانده مشتریان تا اینجا {remaining_total} هست.

💡 کل حجم خریداری شده توسط مشتریان {total_sale} است.
    """
    await update.message.reply_text(txt)
