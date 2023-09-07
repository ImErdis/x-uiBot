import base64
import datetime
import json
import uuid

from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler,
)

import util
from callback import admin
from configuration import Config

config = Config('configuration.yaml')

servers = config.get_db().servers
resellers = config.get_db().resellers
subs = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients
domain = config.website

ACCOUNT = {}
NAME, TRAFFIC, CUSTOM_TRAFFIC, DURATION, CUSTOM_DURATION, GROUP = range(6)


async def renew_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    _id = query.data.split('_')[1]
    print(_id)
    client = clients.find_one({'_id': _id, 'reseller': query.from_user.id, 'active': False})
    if not client:
        return ConversationHandler.END

    ACCOUNT[f'{query.from_user.id}'] = {
        '_id': _id
    }

    text = """💡 لطفا *حجم دلخواه* رو انتخاب کنید.
_(توجه داشته باشید که به ازای هر ماه حجم چند برابر میشه. مثال: 25 گیگ * 2 ماه = 50 گیگ)_"""
    keyboard = [[InlineKeyboardButton("⚡️ 10GB", callback_data="create_account_traffic_10"),
                 InlineKeyboardButton("⚡️ 25GB", callback_data="create_account_traffic_25"),
                 InlineKeyboardButton("⚡️ 50GB", callback_data="create_account_traffic_50"),
                 InlineKeyboardButton("⚡️ 100GB", callback_data="create_account_traffic_100")],
                [InlineKeyboardButton("💡 مقدار دلخواه", callback_data="create_account_traffic_custom")],
                [InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return TRAFFIC


async def custom_traffic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    if int(update.message.text) >= 10:
        ACCOUNT[f'{user.id}']['traffic'] = int(update.message.text)
        text = "⏳ لطفا *مدت زمان* را انتخاب کنید." + "\n" + "_(توجه داشته باشید که به ازای هر ماه حجم چند برابر میشه. مثال: 25 گیگ * 2 ماه = 50 گیگ)_"

        keyboard = [
            [InlineKeyboardButton("⌚️ 1 ماه", callback_data="create_account_duration_1"),
             InlineKeyboardButton("⌚️ 2 ماه", callback_data="create_account_duration_2"),
             InlineKeyboardButton("⌚️ 3 ماه", callback_data="create_account_duration_3")],
            [InlineKeyboardButton("💡 مقدار دلخواه", callback_data="create_account_duration_custom")],
            [InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return DURATION

    keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """

        لطفا *⚡️ مقدار دلخواه*_(گیگ)_ رو ارسال کنید.

        _(حجم _*حداقل باید 10 گیگابایت*_ باشه)_"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return CUSTOM_TRAFFIC


async def traffic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data.split('_')[3] == 'custom':
        keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """

        لطفا *⚡️ مقدار دلخواه*_(گیگ)_ رو ارسال کنید.

        _(حجم حداقل باید 10 گیگابایت باشه)_"""

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return CUSTOM_TRAFFIC

    ACCOUNT[f'{user.id}']['traffic'] = int(query.data.split('_')[3])

    text = "⏳ لطفا *مدت زمان* را انتخاب کنید." + "\n" + "_(توجه داشته باشید که به ازای هر ماه حجم چند برابر میشه. مثال: 25 گیگ * 2 ماه = 50 گیگ)_"

    keyboard = [
        [InlineKeyboardButton("⌚️ 1 ماه", callback_data="create_account_duration_1"),
         InlineKeyboardButton("⌚️ 2 ماه", callback_data="create_account_duration_2"),
         InlineKeyboardButton("⌚️ 3 ماه", callback_data="create_account_duration_3")],
        [InlineKeyboardButton("💡 مقدار دلخواه", callback_data="create_account_duration_custom")],
        [InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return DURATION


async def custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    if int(update.message.text) >= 30:
        ACCOUNT[f'{user.id}']['duration'] = int(update.message.text) / 30

        keyboard = [
                       [InlineKeyboardButton(f"{group['name']}", callback_data=f"create_account_group_{group['_id']}")]
                       for
                       group in groups.find({'status': "Active"})
                   ] + [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "⭐️ لطفا یک *گروه از سرور ها* رو انتخاب کنید." + '\n'

        for group in groups.find({'status': "Active"}):
            svs = [x['name'] for x in servers.find({}) if x['_id'] in group['servers']]
            text += f"\n*{group['name']}*: _{'_, _'.join(svs)}_"

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return GROUP

    keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """

        لطفا *⌚️ مقدار دلخواه*_(روز)_ رو ارسال کنید.

        _(مدت زمان _*حداقل باید 30 روز*_ باشه)_"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return CUSTOM_DURATION


async def duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data.split('_')[3] == 'custom':
        keyboard = [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """

            لطفا *⌚️ مقدار دلخواه*_(روز)_ رو ارسال کنید.

            _(مدت زمان حداقل باید 30 روز باشه)_"""

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return CUSTOM_DURATION
    ACCOUNT[f'{user.id}']['duration'] = int(query.data.split('_')[3])

    keyboard = [
                   [InlineKeyboardButton(f"{group['name']}", callback_data=f"create_account_group_{group['_id']}")] for
                   group in groups.find({'status': "Active"})
               ] + [[InlineKeyboardButton("⏪ بازگشت به پنل ادمین", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "⭐️ لطفا یک *گروه از سرور ها* رو انتخاب کنید." + '\n'

    for group in groups.find({'status': "Active"}):
        svs = [x['name'] for x in servers.find({}) if x['_id'] in group['servers']]
        text += f"\n*{group['name']}*: _{'_, _'.join(svs)}_"

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return GROUP


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    reseller = resellers.find_one({'_id': user.id}) or resellers.find_one({'_id': f"{user.id}"})
    if not reseller:
        return ConversationHandler.END
    idi = uuid.UUID(ACCOUNT[f'{query.from_user.id}']['_id'])
    client = clients.find_one({'_id': ACCOUNT[f'{query.from_user.id}']['_id'], 'reseller': query.from_user.id, 'active': False})
    if not client:
        return ConversationHandler.END
    subscrpt = f'http://{domain}/subscription?uuid={idi}'
    group = groups.find_one({'_id': ObjectId(query.data.split('_')[3])})
    client = {
        'name': client['name'],
        '_id':
            str(idi),
        'servers': {},
        'usage_per_server': {},
        'active': True,
        'reseller': user.id,
        'group': group['_id'],
        'traffic': int(ACCOUNT[f'{query.from_user.id}']['duration'] * ACCOUNT[f'{query.from_user.id}']['traffic']),
        'usage': 0,
        'when': (datetime.datetime.now() + datetime.timedelta(
            seconds=int(ACCOUNT[f'{query.from_user.id}']['duration'] * 30 * 24 * 60 * 60))).timestamp(),
    }
    serv = []
    for server in group['servers']:
        server = servers.find_one({'_id': server})
        inbound = util.get_inbound(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                   server['inbound_id'])
        email = f'{uuid.uuid4()}'[:15]
        util.add_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                        server['inbound_id'],
                        util.generate_client(0, client['traffic'],
                                             int(ACCOUNT[f'{query.from_user.id}']['duration'] * 30 * 24 * 60 * 60),
                                             email,
                                             idi))
        streamSettings = json.loads(inbound['streamSettings'])
        serv.append("`vmess://" + base64.b64encode(
            json.dumps(
                {'id': str(idi), 'aid': '0', 'v': '2', 'tls': streamSettings['security'], 'add': server['domain'],
                 'port': inbound['port'],
                 'type': streamSettings['tcpSettings']['header']['type'] if streamSettings['network'] == 'tcp' else
                 streamSettings['wsSettings']['headers'].get('type', ''),
                 'net': streamSettings['network'],
                 'path': streamSettings['tcpSettings']['header']['request']['path'] if streamSettings[
                                                                                           'network'] == 'tcp' else
                 streamSettings['wsSettings']['path'], 'host': '',
                 'ps': client['name'] + ' ' + server['name']}, sort_keys=True).encode(
                'utf-8')).decode() + '`\n' + f'{server["name"]}')
        client['servers'][f"{server['_id']}"] = email
        client['usage_per_server'][f"{server['_id']}"] = 0
    clients.update_one({'_id': ACCOUNT[f'{query.from_user.id}']['_id'], 'reseller': query.from_user.id, 'active': False}, {'$set': client})
    await query.edit_message_text(
        f"اسم اکانت: \n{client['name']}\n\n" + '\n\n'.join(
            serv) + '\n\n🍩 لینک اشتراک: \n`' + subscrpt + '`', parse_mode='markdown'
    )
    resellers.update_one({'_id': user.id}, {
        '$inc': {'purchased_amount': int(reseller['ppg']) * client['traffic'] + int((ACCOUNT[f'{query.from_user.id}']['duration']-1) * 15000)}
    })
    profit = int(reseller['ppg']) * client['traffic']
    pure_profit = profit - (client['traffic'] * 700 + int(ACCOUNT[f'{query.from_user.id}']['duration'] * 7000))
    await update.get_bot().send_message(config.admin,
                                        f"""✅ Account {client['name']} has been purchased by {user.full_name}_({user.id})_.

💸 The purchased subscription is {ACCOUNT[f'{query.from_user.id}']['traffic']}GB for {ACCOUNT[f'{query.from_user.id}']['duration'] * 30} days.

The net profit from this purchase amounts to {pure_profit}T. _(Total Income: {profit})_""", parse_mode='markdown')
    return ConversationHandler.END


conv_handler = ConversationHandler(per_message=False,
                                   entry_points=[CallbackQueryHandler(renew_account, pattern='^renew_')],
                                   states={
                                       GROUP: [CallbackQueryHandler(group, pattern='^create_account_group_')],
                                       TRAFFIC: [CallbackQueryHandler(traffic, '^create_account_traffic_')],
                                       CUSTOM_TRAFFIC: [MessageHandler(filters.Regex("^\d"), custom_traffic)],
                                       DURATION: [CallbackQueryHandler(duration, '^create_account_duration_')],
                                       CUSTOM_DURATION: [MessageHandler(filters.Regex("^\d"), custom_duration)]
                                   },
                                   fallbacks=[
                                       CallbackQueryHandler(admin.admin, pattern="^cancel$")], allow_reentry=True,
                                   )
