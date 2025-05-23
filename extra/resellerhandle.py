import datetime

import pymongo
import telegram.error
from telegram import Update
from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton

from configuration import Config

config = Config('configuration.yaml')
resellers = config.get_db().resellers
clients = config.get_db().clients


###########################
#         Methods         #
###########################
def add_user(user_id: int, prepayment: bool, ppg: int) -> bool:
    """Adds a reseller to the database

    :param user_id: Reseller Telegram Numeral ID
    :param prepayment: Determines whether reseller has to pay first
    :param ppg: The amount reseller is going to pay for each GB
    :return: Boolean whether reseller added or not
    """
    resellers.insert_one({
        '_id': int(user_id),
        'balance': 0,
        'purchased_amount': 0,
        'prepayment': prepayment,
        'ppg': int(ppg),
        'clients': []
    })

    return True


def generate_accounts_list(page: int, reseller: int):
    accounts = clients.find({'reseller': reseller, 'active': True}).sort(
        [("traffic", pymongo.ASCENDING), ("usage", pymongo.DESCENDING)])
    accounts_count = clients.count_documents({'reseller': reseller, 'active': True})

    keyboard = [[InlineKeyboardButton('🔍 اسم', callback_data='notabutton'),
                 InlineKeyboardButton('⚡️ حجم', callback_data='notabutton'),
                 InlineKeyboardButton('⌚️ تاریخ انقضا', callback_data='notabutton')]] + [
                   [InlineKeyboardButton(x['name'], callback_data=f'account-info_{x["_id"]}'),
                    InlineKeyboardButton(f"{round(x['usage'], 2)}/{x['traffic']}",
                                         callback_data=f'account-info_{x["_id"]}'),
                    InlineKeyboardButton(f"{datetime.datetime.fromtimestamp(x['when']).strftime('%Y/%m/%d')}",
                                         callback_data=f'account-info_{x["_id"]}')]
                   for x in
                   accounts[(page - 1) * 28:page * 28]
               ]
    pagination_buttons = []
    pagination_buttons.append(InlineKeyboardButton("صفحه قبل ⬅️",
                                                   callback_data=f'accounts_reseller_{page - 1}')) if page > 1 else None
    pagination_buttons.append(InlineKeyboardButton("➡️ صفحه بعد",
                                                   callback_data=f'accounts_reseller_{page + 1}')) if accounts_count - page * 28 > 0 else None
    keyboard.append(pagination_buttons) if pagination_buttons else None
    keyboard.append([InlineKeyboardButton("🔍 جست‌وجو کاربر", callback_data="search_user")])
    keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")])
    return keyboard


def generate_reseller_info_keyboard(reseller_id: int):
    reseller = resellers.find_one({'_id': reseller_id})

    row_1 = [[
        InlineKeyboardButton('⚡️ حجم خریداری شده', callback_data='notabutton'),
        InlineKeyboardButton('💰 نرخ هر گیگابایت', callback_data='notabutton'),

    ]]
    row_2 = [[
        InlineKeyboardButton(f'{int(reseller["purchased_amount"]) / int(reseller["ppg"])} گیگابایت',
                             callback_data='notabutton'),
        InlineKeyboardButton(f'{reseller["ppg"]}ت', callback_data='notabutton')
    ]]
    keyboard = row_1 + row_2 + [[InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")]]

    return keyboard


def generate_account_info_keyboard(_id: str, reseller_id: int):
    account = clients.find_one({'reseller': reseller_id, '_id': _id})
    keyboard = []
    if account['active']:
        keyboard.append([
            InlineKeyboardButton('⚡️ حجم باقی‌مانده', callback_data='notabutton'),
            InlineKeyboardButton('⏳ زمان باقی‌مانده', callback_data='notabutton')
        ])
        keyboard.append([
            InlineKeyboardButton(f'{account["traffic"] - int(account["usage"])} گیگابایت', callback_data='notabutton'),
            InlineKeyboardButton(
                f'{(datetime.datetime.fromtimestamp(account["when"]) - datetime.datetime.now()).days} روز',
                callback_data='notabutton')
        ])
    else:
        keyboard.append([
            InlineKeyboardButton('🔄 تمدید اکانت', callback_data=f'renew_{account["_id"]}')
        ])
    keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")])

    return keyboard


async def generate_reseller_list(page: int, update: Update):
    rs = resellers.find({})
    rs_count = resellers.count_documents({})
    keyboard = [[
        InlineKeyboardButton('💰 موجودی', callback_data='notabutton'),
        InlineKeyboardButton('📱 یوزرنیم', callback_data='notabutton')
    ]]
    for x in rs[(page - 1) * 30:page * 30]:
        try:
            chat = await update.get_bot().get_chat(x["_id"])
        except telegram.error.BadRequest:
            continue
        keyboard.append([
            InlineKeyboardButton(f'{x["balance"] - x["purchased_amount"]}ت', callback_data=f'reseller_{x["_id"]}'),
            InlineKeyboardButton(f'{chat.username}', callback_data=f'reseller_{x["_id"]}')
        ])
    pagination_buttons = []
    pagination_buttons.append(InlineKeyboardButton("صفحه قبل ⬅️",
                                                   callback_data=f'accounts_reseller_{page - 1}')) if page > 1 else None
    pagination_buttons.append(InlineKeyboardButton("➡️ صفحه بعد",
                                                   callback_data=f'accounts_reseller_{page + 1}')) if rs_count - page * 30 > 0 else None
    keyboard.append(pagination_buttons) if pagination_buttons else None
    keyboard.append([InlineKeyboardButton("📨 پیام به همه", callback_data="message_reseller_all")])
    keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")])
    return keyboard


async def generate_reseller_info(reseller_id: int, update: Update):
    reseller = resellers.find_one({'_id': reseller_id})
    keyboard = []
    try:
        chat = await update.get_bot().get_chat(reseller["_id"])
        keyboard.append([
            InlineKeyboardButton('💰 موجودی', callback_data='notabutton'),
            InlineKeyboardButton('📱 یوزرنیم', callback_data='notabutton')
        ])
        keyboard.append([
            InlineKeyboardButton(f'{reseller["balance"] - reseller["purchased_amount"]}T',
                                 callback_data=f'notabutton'),
            InlineKeyboardButton(f'{chat.username}', callback_data=f'notabutton')
        ])
        keyboard.append([
            InlineKeyboardButton('❌ غیرفعال سازی', callback_data=f'disable_reseller_{reseller["_id"]}') if reseller.get(
                'enable', True) else InlineKeyboardButton('✅ فعال سازی',
                                                           callback_data=f'enable_reseller_{reseller["_id"]}')
        ])
        keyboard.append([InlineKeyboardButton("📨 پیام به نماینده", callback_data=f'message_reseller_{reseller["_id"]}')])
    except telegram.error.BadRequest:
        pass
    keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")])
    return keyboard
