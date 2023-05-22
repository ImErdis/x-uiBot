from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)
from configuration import Config

config = Config('configuration.yaml')

groups = config.get_db().groups
subs = config.get_db().subscriptions

GROUP, NAME, DURATION, USERS, TRAFFIC = range(5)
SUBSCRIPTION = {}
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_create_subscription")]
])


async def create_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    if not groups.find({}):
        await query.edit_message_text('برای ساخت اشتراک حداقل باید یک گروه وجود داشته باشد',
                                      reply_markup=InlineKeyboardMarkup(
                                          [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))
        return ConversationHandler.END

    group_list = [x for x in groups.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'group_{x["name"]}'),
         InlineKeyboardButton('✅' if x['status'] == "Active" else '❌',
                              callback_data=f'group_{x["name"]}')] for x in group_list
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_create_subscription")])

    await query.edit_message_text("گروه مورد نظر را انتخاب کنید", reply_markup=InlineKeyboardMarkup(keyboard))

    return GROUP


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    SUBSCRIPTION[f'{user.id}'] = {
        'name': None,
        'duration': 0,
        'group': query.data[6:],
        'users': 0,
        'traffic': 0
    }

    await query.edit_message_text("لطفا اسم اشتراک را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    if subs.find_one({'group': SUBSCRIPTION[f'{user.id}']['group'], 'name': update.message.text}):
        await update.message.reply_text('نام هر اشتراک باید متفاوت باشد لطفا نام جدید بفرستید',
                                        reply_markup=reply_markup)
        return NAME

    SUBSCRIPTION[f'{user.id}']['name'] = update.message.text

    await update.message.reply_text(
        "رواله, "
        "حالا مدت زمانشو به ثانیه بفرست.", reply_markup=reply_markup
    )

    return DURATION


async def duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user

    SUBSCRIPTION[f'{user.id}']['duration'] = int(update.message.text)

    await update.message.reply_text(
        "رواله, "
        "حالا حجمو به گیگ برام بفرست.", reply_markup=reply_markup
    )

    return TRAFFIC


async def traffic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user

    SUBSCRIPTION[f'{user.id}']['traffic'] = int(update.message.text)

    await update.message.reply_text(
        "رواله, "
        "حالا تعداد یوزرای مجازو برام بفرست.", reply_markup=reply_markup
    )

    return USERS


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    SUBSCRIPTION[f'{user.id}']['allowed_users'] = int(update.message.text)
    subs.insert_one(SUBSCRIPTION[f'{user.id}'])
    del SUBSCRIPTION[f'{user.id}']
    await update.message.reply_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

    return ConversationHandler.END


async def cancel_remove_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query

    await query.answer()
    await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[
                                       CallbackQueryHandler(create_subscription, pattern='^create_subscription$')],
                                   states={
                                       GROUP: [CallbackQueryHandler(group, pattern='^group_')],
                                       NAME: [MessageHandler(filters.TEXT, name)],
                                       DURATION: [MessageHandler(filters.Regex("^\d"), duration)],
                                       TRAFFIC: [MessageHandler(filters.Regex("^\d"), traffic)],
                                       USERS: [MessageHandler(filters.Regex("^\d"), users)]
                                   },
                                   fallbacks=[CallbackQueryHandler(cancel_remove_server,
                                                                   pattern="^cancel_create_subscription$")],
                                   )
