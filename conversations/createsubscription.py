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

servers = config.get_db().servers
subs = config.get_db().subscriptions

NAME, DURATION, USERS, TRAFFIC, SERVERS = range(5)
SUBSCRIPTION = {}
reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("بازگشت ◀️", callback_data="cancel_create_subscription")]
])


async def create_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    await query.answer()

    if not servers.find({}):
        await query.edit_message_text('برای ساخت اشتراک حداقل باید یک سرور وجود داشته باشد',
                                      reply_markup=InlineKeyboardMarkup(
                                          [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))
        return ConversationHandler.END

    await query.edit_message_text("لطفا اسم اشتراک را ارسال کنید.", reply_markup=reply_markup)

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    user = update.message.from_user
    if subs.find_one({'name': update.message.text}):
        await update.message.reply_text('نام هر اشتراک باید متفاوت باشد لطفا نام جدید بفرستید',
                                        reply_markup=reply_markup)
        return NAME

    SUBSCRIPTION[f'{user.id}'] = {
        'name': update.message.text,
        'duration': 0,
        'servers': [],
        'users': 0,
        'traffic': 0,
        'clients': []
    }

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

    servers_list = [x for x in servers.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'subserver_{x["name"]}'),
         InlineKeyboardButton('✅' if x['_id'] in SUBSCRIPTION[f'{user.id}'].get('servers', []) else '❌',
                              callback_data=f'subserver_{x["name"]}')] for x in servers_list
    ]
    keyboard.append([InlineKeyboardButton('✅' + ' مرحله بعد', callback_data='create_subscription_done')])

    await update.message.reply_text(
        "رواله, "
        "سرورایی ک میخوای تو اشتراک باشن رو انتخاب کن.", reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SERVERS


async def subservers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sent server message"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data != "create_subscription_done":
        server = servers.find_one({'name': query.data[10:]})
        if server['_id'] not in SUBSCRIPTION[f'{user.id}'].get('servers', []):
            SUBSCRIPTION[f'{user.id}']['servers'].append(server['_id'])
        else:
            SUBSCRIPTION[f'{user.id}']['servers'].remove(server['_id'])

    servers_list = [x for x in servers.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'subserver_{x["name"]}'),
         InlineKeyboardButton('✅' if x['_id'] in SUBSCRIPTION[f'{user.id}'].get('servers', []) else '❌',
                              callback_data=f'subserver_{x["name"]}')] for x in servers_list
    ]
    keyboard.append([InlineKeyboardButton('✅' + ' مرحله بعد', callback_data='create_subscription_done')])

    if query.data == "create_subscription_done":
        if not SUBSCRIPTION[f'{user.id}']['servers']:
            await query.edit_message_text(
                "حداقل یک سرور باید انتخاب کنی, "
                "سرورایی ک میخوای تو اشتراک باشن رو انتخاب کن.", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        else:
            subs.insert_one(SUBSCRIPTION[f'{user.id}'])
            del SUBSCRIPTION[f'{user.id}']
            await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید',
                                          reply_markup=InlineKeyboardMarkup(
                                              [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

            return ConversationHandler.END

    await query.edit_message_text(
        "رواله, "
        "سرورایی ک میخوای تو اشتراک باشن رو انتخاب کن.", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cancel_remove_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query

    await query.answer()
    await query.edit_message_text('لطفا برای بازگشت /start یا دکمه زیر را فشار دهید', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton('پنل ادمین', callback_data="admin")]]))

    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
    entry_points=[CallbackQueryHandler(create_subscription, pattern='^create_subscription$')],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        DURATION: [MessageHandler(filters.Regex("^\d"), duration)],
        TRAFFIC: [MessageHandler(filters.Regex("^\d"), traffic)],
        USERS: [MessageHandler(filters.Regex("^\d"), users)],
        SERVERS: [CallbackQueryHandler(subservers, '^subserver_'),
                  CallbackQueryHandler(subservers, '^create_subscription_done$')]
    },
    fallbacks=[CallbackQueryHandler(cancel_remove_server, pattern="^cancel_create_subscription$")],
)
