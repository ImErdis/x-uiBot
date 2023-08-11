from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram._update import Update
from configuration import Config

config = Config('configuration.yaml')
subs = config.get_db().subscriptions
clients = config.get_db().clients
resellers = config.get_db().resellers


async def start(update: Update, context):
    """Sends a welcome message which will greet the user + bot inline buttons."""

    keyboard = [InlineKeyboardButton("📞 ارتباط با ما", callback_data="contact-info")]
    if update.message.from_user.id == config.admin or resellers.find_one({'_id': update.message.from_user.id}) or resellers.find_one({'_id': f"{update.message.from_user.id}"}):
        keyboard.append(
            InlineKeyboardButton("🖥️ پنل", callback_data="admin")
        )

    reply_markup = InlineKeyboardMarkup([keyboard])

    text = """👋 به ربات *VingPN* خوش آمدید!

_"ایمن، ناشناس و متصل به دنیا بمانید"_

🌐 از اینکه سرویس های مارا انتخاب کردید متشکریم"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')



async def remaining(update: Update, context):
    if update.message.from_user.id != config.admin:
        return

    total = 0
    remaining_total = 0
    total_sale = 0
    for client in clients.find({}):
        sub = subs.find_one({'_id': client['subscription']})
        total += client['usage']
        total_sale += sub['traffic']
    for client in clients.find({'active': True}):
        sub = subs.find_one({'_id': client['subscription']})
        remaining_total += sub['traffic'] - client['usage']


    txt = f"""
    💡 کل حجم مصرفی مشتریان تا اینجا {total} هست.

💡 کل حجم باقی مانده مشتریان تا اینجا {remaining_total} هست.

💡 کل حجم خریداری شده توسط مشتریان {total_sale} است.
    """
    await update.message.reply_text(txt)
