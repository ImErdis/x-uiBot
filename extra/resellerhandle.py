import datetime

import pymongo
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
                    InlineKeyboardButton(f"{round(x['usage'], 2)}/{x['traffic']}", callback_data=f'account-info_{x["_id"]}'),
                    InlineKeyboardButton(f"{datetime.datetime.fromtimestamp(x['when']).strftime('%Y/%m/%d')}",
                                         callback_data=f'account-info_{x["_id"]}')]
                   for x in
                   accounts[(page - 1) * 30:page * 30]
               ]
    pagination_buttons = []
    pagination_buttons.append(InlineKeyboardButton("صفحه قبل ⬅️",
                                                   callback_data=f'accounts_reseller_{page - 1}')) if page > 1 else None
    pagination_buttons.append(InlineKeyboardButton("➡️ صفحه بعد",
                                                   callback_data=f'accounts_reseller_{page + 1}')) if accounts_count - page * 30 > 0 else None
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
            InlineKeyboardButton(f'{(datetime.datetime.fromtimestamp(account["when"])-datetime.datetime.now()).days} روز', callback_data='notabutton')
        ])
    else:
        keyboard.append([
            InlineKeyboardButton('🔄 تمدید اکانت', callback_data=f'renew_{account["_id"]}')
        ])
    keyboard.append([InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="admin")])

    return keyboard

