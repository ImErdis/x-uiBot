import datetime
import uuid

import httpx
from bson import ObjectId
from telegram import Update
from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.ext import ContextTypes

import util
from configuration import Config

config = Config('configuration.yaml')

db = config.get_db().clients
servers = config.get_db().servers
subscriptions = config.get_db().subscriptions


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("ساخت اکانت", callback_data="generate_account")],
        [InlineKeyboardButton("لیست اکانت ها", callback_data="list_account")],
        [InlineKeyboardButton("ساخت اشتراک", callback_data="create_subscription")],
        [InlineKeyboardButton("ویرایش اشتراک", callback_data="edit_subscription")],
        [
            InlineKeyboardButton("حذف کردن سرور", callback_data="remove_server"),
            InlineKeyboardButton("اضافه کردن سرور", callback_data="add_server"), ],

        [InlineKeyboardButton("لیست سرورها", callback_data="list_server")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('انتخاب کنید', reply_markup=reply_markup)


async def list_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription_list = [x for x in subscriptions.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'editsub_{x["name"]}'),
         InlineKeyboardButton(f'{len(x["clients"])}/{x["allowed_users"]}',
                              callback_data=f'editsub_{x["name"]}')] for x in subscription_list
    ]
    text = 'حالا اشتراک مورد نظرت برای ویرایش انتخاب کن' if keyboard else 'متاسفانه هیچ اشتراکی نداری'
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription = subscriptions.find_one({'name': query.data[8:]})
    keyboard = [[InlineKeyboardButton('ویرایش سرور ها', callback_data=f'changeserver_{subscription["name"]}')],
                [InlineKeyboardButton("بازگشت ◀️", callback_data="admin")]]

    text = 'چه کاری میخواید روی اشتراک انجام بدید؟'
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_subscription_servers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
    if len(query.data.split('_')) == 3:
        server = servers.find_one({'name': query.data.split('_')[2]})
        if server['_id'] not in subscription['servers']:
            subscriptions.update_one({'_id': subscription['_id']}, {'$push': {'servers': server['_id']}})
        else:
            subscriptions.update_one({'_id': subscription['_id']}, {'$pull': {'servers': server['_id']}})
    subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
    servers_list = [x for x in servers.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'changeserver_{subscription["name"]}_{x["name"]}'),
         InlineKeyboardButton('✅' if x['_id'] in subscription['servers'] else '❌',
                              callback_data=f'changeserver_{subscription["name"]}_{x["name"]}')] for x in servers_list
    ]
    keyboard.append(
        [InlineKeyboardButton('✅' + ' آپدیت کردن اشتراک برای مشتریان فعلی',
                              callback_data=f'updatesub_{subscription["name"]}')])
    keyboard.append([InlineKeyboardButton("پنل ادمین ◀️", callback_data="admin")])

    text = 'سرور هارو انتخاب کنید'
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def update_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    timed_out = []
    subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
    for client in subscription['clients']:
        for sv in list(client['servers'].keys()):
            if ObjectId(sv) not in subscription['servers']:
                server = servers.find_one({'_id': ObjectId(sv)})
                if sv not in timed_out:
                    try:
                        util.remove_client(f'http://{server["ip"]}:{server["port"]}',
                                           server['user'],
                                           server['password'], client['servers'][sv])
                    except ModuleNotFoundError:
                        None
                    except httpx.ConnectTimeout:
                        timed_out.append(sv)
                        None
                del client['servers'][sv]
        for sv in subscription['servers']:
            if ObjectId(sv) not in client['servers']:
                server = servers.find_one({'_id': ObjectId(sv)})
                email = f'{uuid.uuid4()}'[:15]
                util.add_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
                                server['inbound_id'],
                                util.generate_client(0, subscription['traffic'],
                                                     client['when'] - datetime.datetime.now().timestamp(), email,
                                                     client['_id']))
                client['servers'][f"{server['_id']}"] = email
    subscriptions.update_one({'_id': subscription['_id']}, {'$set': subscription})

    await query.edit_message_text('تمامی مشتریان فعلی آپدیت شدند!', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("پنل ادمین ◀️", callback_data="admin")]]))


async def list_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription_list = [x for x in subscriptions.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'listaccountsub_{x["name"]}'),
         InlineKeyboardButton(f'{len(x["clients"])}/{x["allowed_users"]}',
                              callback_data=f'listaccountsub_{x["name"]}')] for x in subscription_list if
        len(x['clients']) >= 1
    ]
    text = 'حالا اشتراک مورد نظرت برای دیدن کاربراشو انتخاب کن' if keyboard else 'متاسفانه تو هیچ اشتراکی کاربر نداری'
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def subscription_list_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subscription = subscriptions.find_one({'name': query.data[15:]})
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'listaccount_{subscription["name"]}_{x["name"]}'),
         InlineKeyboardButton(f"{x['usage']}/{subscription['traffic']}",
                              callback_data=f'listaccount_{subscription["name"]}_{x["name"]}')] for x in
        subscription['clients']
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text('کاربر مورد نظرتو انتخاب کن', reply_markup=InlineKeyboardMarkup(keyboard))


async def control_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
    for client in subscription['clients']:
        if client['name'] == query.data.split('_')[2]:
            keyboard = [
                [InlineKeyboardButton('حذف کاربر',
                                      callback_data=f'controlaccountdelete_{subscription["name"]}_{client["name"]}')]
            ]
            text = f'{client["name"]}\nUsage: {client["usage"]}/{subscription["traffic"]}'
            keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
    for client in subscription['clients']:
        if client['name'] == query.data.split('_')[2]:
            for sv in subscription['servers']:
                server = servers.find_one({'_id': sv})
                try:
                    util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'],
                                       server['password'], client['servers'][f"{server['_id']}"])
                except ModuleNotFoundError:
                    pass
            subscription['clients'].remove(client)
    subscriptions.update_one({'name': query.data.split('_')[1]}, {'$set': {'clients': subscription['clients']}})

    await query.edit_message_text('با موفقیت حذف شد', reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("پنل ادمین", callback_data="admin")]]))


async def list_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    servers_list = [x for x in servers.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'server_{x["name"]}')] for x in
        servers_list
    ]
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text('لیست سرور ها', reply_markup=reply_markup)


async def control_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    server = servers.find_one({'name': f'{query.data[7:]}'})
    panel_addy = f'http://{server["ip"]:{server["port"]}}'
    text_en = f"*Server Name*: {server['name']}\n*Panel Addy*: {panel_addy}\n*Inbound Id*: {server['inbound_id']}"

    keyboard = [[InlineKeyboardButton('جایگذین', callback_data=f'replaceserver_{server["_id"]}')],
                [InlineKeyboardButton('❌ حذف', callback_data=f'deleteserver_{server["_id"]}')],
                [InlineKeyboardButton("بازگشت ◀️", callback_data="admin")]]

    await query.edit_message_text(text_en, reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    server = servers.find_one({'_id': ObjectId(query.data[13:])})
    timeout = False
    panel_addy = f'http://{server["ip"]:{server["port"]}}'

    for sub in subscriptions.find():
        try:
            sub['servers'].remove(server['_id'])
        except ValueError:
            None
        for client in sub['clients']:
            if not timeout:
                try:
                    util.remove_client(panel_addy, server['user'],
                                       server['password'], client['servers'][f"{server['_id']}"])
                except KeyError:
                    None
                except ModuleNotFoundError:
                    None
                except httpx.ConnectTimeout:
                    timeout = True
                    None
            if hasattr(client['servers'], f"{server['_id']}"):
                del client['servers'][f"{server['_id']}"]

        subscriptions.update_one({'_id': sub['_id']}, {'$set': sub})

    servers.delete_one({'_id': server['_id']})

    text = 'سرور با موفقیت حذف شد ✅'
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("پنل ادمین", callback_data="admin")]]))
