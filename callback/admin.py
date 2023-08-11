import datetime
import uuid

import httpx
from bson import ObjectId
from telegram import Update
from telegram._inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram._inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import util
from configuration import Config
from extra import resellerhandle

config = Config('configuration.yaml')

db = config.get_db().clients
servers = config.get_db().servers
subscriptions = config.get_db().subscriptions
groups = config.get_db().groups
clients = config.get_db().clients
resellers = config.get_db().resellers


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    keyboard = []
    if query.from_user.id == config.admin:
        text = """🔒 پنل وی‌پی‌ان *وینگ*"""
        keyboard += [
            # [InlineKeyboardButton("ساخت اکانت", callback_data="generate_account")],
            # [InlineKeyboardButton("لیست اکانت ها", callback_data="list_account")],
            # [InlineKeyboardButton("بازیابی اکانت", callback_data="restore_account")],
            # [InlineKeyboardButton("ساخت اشتراک", callback_data="create_subscription"),
            [InlineKeyboardButton('ساخت گروه', callback_data="create_group")],
            # [InlineKeyboardButton("ویرایش اشتراک", callback_data="none"),
            #  InlineKeyboardButton("ویرایش گروه", callback_data="edit_group")],
            # [InlineKeyboardButton("اضافه کردن سرور", callback_data="add_server")],
            # [InlineKeyboardButton("لیست سرورها", callback_data="list_server")],
            [InlineKeyboardButton("➕ اضافه کردن نماینده", callback_data="add_reseller")]
        ]
    reseller = resellers.find_one({'_id': query.from_user.id}) or resellers.find_one({'_id': f"{query.from_user.id}"})
    if reseller:
        ppg = reseller['ppg']
        text = f"""🔒 پنل وی‌پی‌ان *وینگ*.

نرخ فعلی شما به ازای هر گیگابایت: *{ppg}*

_🌐 به کانال ما (@VingPN) برای اطلاعات بیشتر مراجعه کنید._"""
        keyboard += [
            [InlineKeyboardButton("💼 اطلاعات حساب", callback_data="information_reseller"),
             InlineKeyboardButton("👥 لیست اکانت ها", callback_data="accounts_reseller_1")],
            [InlineKeyboardButton("🔨 ساخت اکانت", callback_data="create_account")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END


async def accounts_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    reseller = resellers.find_one({'_id': query.from_user.id})
    if not reseller:
        return
    page = int(query.data.split('_')[2])

    keyboard = resellerhandle.generate_accounts_list(page, query.from_user.id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""🗒️ مشتریان *فعال* کنونی شما به شرح زیر میباشد.

_🌐 به کانال ما (@VingPN) برای اطلاعات بیشتر مراجعه کنید._"""
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def account_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    reseller = resellers.find_one({'_id': query.from_user.id})
    if not reseller:
        return

    _id = query.data.split('_')[1]
    client = clients.find_one({'_id': _id, 'reseller': reseller['_id']})
    if not client:
        return

    keyboard = resellerhandle.generate_account_info_keyboard(_id, reseller['_id'])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
    💼 اطلاعات *اکانت*. _(وضعیت: {'🟢 فعال' if client['active'] else '🔴 غیرفعال'})_

- *📮 نام*: _{client['name']}_
-  *🔑 آیدی*: `{client['_id']} `

_🌐 به کانال ما (@VingPN) برای اطلاعات بیشتر مراجعه کنید._
    """
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def information_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    reseller = resellers.find_one({'_id': query.from_user.id})
    if not reseller:
        return

    keyboard = resellerhandle.generate_reseller_info_keyboard(reseller['_id'])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"""💼 اطلاعات *حساب*.

*- 💰موجودی*: _{reseller["balance"]}_
*- 💸 کل خرید*: _{reseller["purchased_amount"]}_

_🌐 به کانال ما (@VingPN) برای اطلاعات بیشتر مراجعه کنید._"""
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # async def list_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:




#     query = update.callback_query
#     await query.answer()
#
#     subscription_list = [x for x in subscriptions.find({})]
#     keyboard = [
#         [InlineKeyboardButton(x['name'], callback_data=f'editsub_{x["name"]}'),
#          InlineKeyboardButton(f'{len(x["clients"])}/{x["allowed_users"]}',
#                               callback_data=f'editsub_{x["name"]}')] for x in subscription_list
#     ]
#     text = 'حالا اشتراک مورد نظرت برای ویرایش انتخاب کن' if keyboard else 'متاسفانه هیچ اشتراکی نداری'
#     keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])
#
#     await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# async def edit_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#
#     subscription = subscriptions.find_one({'name': query.data[8:]})
#     keyboard = [[InlineKeyboardButton('ویرایش سرور ها', callback_data=f'changeserver_{subscription["name"]}')],
#                 [InlineKeyboardButton("بازگشت ◀️", callback_data="admin")]]
#
#     text = 'چه کاری میخواید روی اشتراک انجام بدید؟'
#     await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# async def edit_subscription_servers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#
#     subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
#     if len(query.data.split('_')) == 3:
#         server = servers.find_one({'name': query.data.split('_')[2]})
#         if server['_id'] not in subscription['servers']:
#             subscriptions.update_one({'_id': subscription['_id']}, {'$push': {'servers': server['_id']}})
#         else:
#             subscriptions.update_one({'_id': subscription['_id']}, {'$pull': {'servers': server['_id']}})
#     subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
#     servers_list = [x for x in servers.find({})]
#     keyboard = [
#         [InlineKeyboardButton(x['name'], callback_data=f'changeserver_{subscription["name"]}_{x["name"]}'),
#          InlineKeyboardButton('✅' if x['_id'] in subscription['servers'] else '❌',
#                               callback_data=f'changeserver_{subscription["name"]}_{x["name"]}')] for x in servers_list
#     ]
#     keyboard.append(
#         [InlineKeyboardButton('✅' + ' آپدیت کردن اشتراک برای مشتریان فعلی',
#                               callback_data=f'updatesub_{subscription["name"]}')])
#     keyboard.append([InlineKeyboardButton("پنل ادمین ◀️", callback_data="admin")])
#
#     text = 'سرور هارو انتخاب کنید'
#     await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# async def update_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()
#     timed_out = []
#     subscription = subscriptions.find_one({'name': query.data.split('_')[1]})
#     for client in subscription['clients']:
#         for sv in list(client['servers'].keys()):
#             if ObjectId(sv) not in subscription['servers']:
#                 server = servers.find_one({'_id': ObjectId(sv)})
#                 if sv not in timed_out:
#                     try:
#                         util.remove_client(f'http://{server["ip"]}:{server["port"]}',
#                                            server['user'],
#                                            server['password'], client['servers'][sv])
#                     except TypeError:
#                         None
#                     except ModuleNotFoundError:
#                         None
#                     except httpx.ConnectTimeout:
#                         timed_out.append(sv)
#                         None
#                     except httpx.ConnectError:
#                         timed_out.append(sv)
#                         None
#                 del client['servers'][sv]
#         for sv in subscription['servers']:
#             if f"{sv}" not in client['servers'].keys():
#                 server = servers.find_one({'_id': ObjectId(sv)})
#                 email = f'{uuid.uuid4()}'[:15]
#                 util.add_client(f'http://{server["ip"]}:{server["port"]}', server['user'], server['password'],
#                                 server['inbound_id'],
#                                 util.generate_client(0, subscription['traffic'],
#                                                      client['when'] - datetime.datetime.now().timestamp(), email,
#                                                      client['_id']))
#                 client['servers'][f"{server['_id']}"] = email
#     subscriptions.update_one({'_id': subscription['_id']}, {'$set': subscription})
#
#     await query.edit_message_text('تمامی مشتریان فعلی آپدیت شدند!', reply_markup=InlineKeyboardMarkup(
#         [[InlineKeyboardButton("پنل ادمین ◀️", callback_data="admin")]]))


async def list_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    group_list = [x for x in groups.find({})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'listaccountgroup_{x["name"]}')] for x in group_list
    ]
    text = 'حالا گروه مورد نظرت برای دیدن کاربراشو انتخاب کن'
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def group_list_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription_list = [x for x in subscriptions.find({'group': query.data.split('_')[1]})]
    keyboard = [
        [InlineKeyboardButton(x['name'], callback_data=f'listaccountsub_{x["name"]}_{x["group"]}_1'),
         InlineKeyboardButton(f'{clients.count_documents({"subscription": x["_id"], "active": True})}',
                              callback_data=f'listaccountsub_{x["name"]}_{x["group"]}_1')] for x in subscription_list
    ]
    text = 'حالا اشتراک مورد نظرت برای دیدن کاربراشو انتخاب کن'

    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def subscription_list_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split('_')[3])
    subscription = subscriptions.find_one({'name': query.data.split('_')[1], 'group': query.data.split('_')[2]})
    keyboard = [
        [InlineKeyboardButton(x['name'],
                              callback_data=f'listaccount_{subscription["name"]}_{subscription["group"]}_{x["name"]}'),
         InlineKeyboardButton(f"{round(x['usage'], 2)}/{subscription['traffic']}",
                              callback_data=f'listaccount_{subscription["name"]}_{subscription["group"]}_{x["name"]}'),
         InlineKeyboardButton(f"{datetime.datetime.fromtimestamp(x['when']).strftime('%Y/%m/%d')}",
                              callback_data=f'listaccount_{subscription["name"]}_{subscription["group"]}_{x["name"]}')]
        for x in
        clients.find({'subscription': subscription['_id'], 'active': True})[(page - 1) * 32:page * 32]
    ]
    clients_count = clients.count_documents({'subscription': subscription['_id']})
    pagination_buttons = []
    pagination_buttons.append(InlineKeyboardButton("◀️",
                                                   callback_data=f'listaccountsub_{subscription["name"]}_{subscription["group"]}_{page - 1}')) if page > 1 else None
    pagination_buttons.append(InlineKeyboardButton("➡️",
                                                   callback_data=f'listaccountsub_{subscription["name"]}_{subscription["group"]}_{page + 1}')) if clients_count - page * 32 > 0 else None
    keyboard.append(pagination_buttons) if pagination_buttons else None
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])

    await query.edit_message_text('کاربر مورد نظرتو انتخاب کن', reply_markup=InlineKeyboardMarkup(keyboard))


async def control_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subscription = subscriptions.find_one({'name': query.data.split('_')[1], 'group': query.data.split('_')[2]})
    client = clients.find_one({'name': query.data.split('_')[3]})
    keyboard = [
        [InlineKeyboardButton('حذف کاربر',
                              callback_data=f'controlaccountdelete_{subscription["name"]}_{subscription["group"]}_{client["name"]}')]
    ]
    text = f'{client["name"]}\nUsage: {client["usage"]}/{subscription["traffic"]}'
    keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="admin")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    subscription = subscriptions.find_one({'name': query.data.split('_')[1], 'group': query.data.split('_')[2]})
    client = clients.find_one({'name': query.data.split('_')[3], 'subscription': subscription['_id']})
    for server_id in client['servers']:
        server = servers.find_one({'_id': server_id})
        try:
            util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'],
                               server['password'], client['servers'][f"{server['_id']}"])
        except ModuleNotFoundError:
            pass
    clients.update_one({'name': query.data.split('_')[3], 'subscription': subscription['_id']},
                       {'$set': {'active': False}})

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
        group = groups.find_one({'name': sub['group']})
        if server['_id'] not in group['servers']:
            pass
        for client in sub['clients']:
            if not timeout:
                try:
                    util.remove_client(f'http://{server["ip"]}:{server["port"]}', server['user'],
                                       server['password'], client['servers'][f"{server['_id']}"])
                except KeyError:
                    None
                except ModuleNotFoundError:
                    None
                except httpx.ConnectTimeout:
                    timeout = True
                    None
                except httpx.ConnectError:
                    timeout = True
                    None
            if hasattr(client['servers'], f"{server['_id']}"):
                del client['servers'][f"{server['_id']}"]

        subscriptions.update_one({'_id': sub['_id']}, {'$set': sub})

        try:
            group['servers'].remove(server['_id'])
            groups.update_one({'_id': group['_id']}, {'$set': group})
        except ValueError:
            None
        servers.delete_one({'_id': server['_id']})

        text = 'سرور با موفقیت حذف شد ✅'
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("پنل ادمین", callback_data="admin")]]))
