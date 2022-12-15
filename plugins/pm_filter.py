# Kanged From @TroJanZheX
import asyncio
import re
import ast

from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, DELETE_TIME, P_TTI_SHOW_OFF, IMDB, REDIRECT_TO, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, START_IMAGE_URL, UNAUTHORIZED_CALLBACK_TEXT, redirected_env
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}


@Client.on_message((filters.group | filters.private) & filters.text & ~filters.edited & filters.incoming)
async def give_filter(client, message):
    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer("You are using one of my old messages, please send the request again.", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    pre = 'Chat' if settings['redirect_to'] == 'Chat' else 'files'

    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"📂 [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                )
            ] 
            for file in files
        ]
    else:
        btn = [        
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f'{pre}_#{file.file_id}#{query.from_user.id}',
                )
            ] 
            for file in files
        ]

    btn.insert(0, 
        [
            InlineKeyboardButton(f'🌀 {search} 🌀', 'moviesheading')
        ]
    )
    btn.insert(1,
        [
            InlineKeyboardButton(f'📂 ғɪʟᴇs: {len(files)}', 'dupe'),
            InlineKeyboardButton(f'🎁 ᴛɪᴘs', 'tips'),
            InlineKeyboardButton(f'📮 ɪɴғᴏ', 'inform')
        ]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⏪ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"📃 ᴘᴀɢᴇs {round(int(offset) / 10) + 1} / {round(total / 10)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("ɴᴇxᴛ ⏩", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⏪ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("ɴᴇxᴛ ⏩", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("search your own 🤨 ", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.message_id)
    if not movies:
        return await query.answer("𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖠𝗀𝖺𝗂𝗇 𝖣𝗎𝖽𝖾, 𝖥𝗂𝗅𝖾 𝖫𝗂𝗇𝗄 𝖾𝗑𝗉𝗂𝗋𝖾𝖽. 😔 ", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('just a second...searching....🧐 ')
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit('This Movie Not Found In DataBase😕, Please check the movie is released in OTT, if yes contact @movieslandadmin_bot to add the movie to DataBase. ')
            await asyncio.sleep(10)
            await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!! 🥴 ", quote=True)
                    return await query.answer('Piracy Is Crime')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups 🥴 ",
                    quote=True
                )
                return await query.answer('Piracy Is Crime 😑')

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('𝗌𝖺𝗇𝗍𝗁𝗈𝗌𝗁𝖺𝗆 𝖺𝗅𝗅𝖾')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == "creator") or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that! 😠 ", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == "creator") or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!! 🤐 ", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode="md"
        )
        return await query.answer('Piracy Is Crime')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode="md")
        return await query.answer('Piracy Is Crime')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('Piracy Is Crime')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)                                                      
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False 
                )
                await query.answer('𝖢𝗁𝖾𝖼𝗄 𝗆𝗒 𝗉𝗆 🤠 , I have sent you 😉', show_alert=True)
        except UserIsBlocked:
            await query.answer('Can't help coz you Blocked me.. plz Unblock the bot mahn ! 😞 ', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    
    elif query.data.startswith("Chat"):
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
            size = size
            mention = mention
        if f_caption is None:
            f_caption = f"{files.file_name}"
            size = f"{files.file_size}"
            mention = f"{query.from_user.mention}"
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("Make sure Bot is admin in Forcesub channel")
            return
        try:
            msg = await client.send_cached_media(
                chat_id=AUTH_CHANNEL,
                file_id=file_id,
                caption=f'<b>Hai 👋 {query.from_user.mention} \n☵☵☵☵☵☵☵☵☵☵☵☵☵\n⚡ Powered by : {query.message.chat.title}\n☵☵☵☵☵☵☵☵☵☵☵☵☵</b>\n\n <code> {title}</code>\n\n⚠️ This file will be deleted in 5 minute as it has copyright ... !!!\n\n Download only After moving from here to saved message or somewhere else..!!!\n\n <b>[🤝Join US](https://t.me/MoviesLandFamily)|[♻️INVITE♻️](https://api.whatsapp.com/send?text=കാണാൻ%20ആഗ്രഹമുള്ള%20ഏതു%20സിനിമയും%20ഏതു%20നേരത്തും%20ചോദിക്കാം%20-%20https://t.me/movieslandfamily/)</b>,',
                protect_content=True if ident == "filep" else False 
            )
            msg1 = await query.message.reply(
                f'<b> Hai 👋 {query.from_user.mention} </b>😍\n\n<b>📫 Your File is Ready</b>\n\n'           
                f'<b>📂 Fɪʟᴇ Nᴀᴍᴇ</b> : [ @cinema_tharavadu ]<code> {title}</code>\n\n'              
                f'<b>⚙️ Fɪʟᴇ Sɪᴢᴇ</b> : <b>{size}</b>',
                True,
                'html',
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton('📥 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝖫𝗂𝗇𝗄 📥 ', url = msg.link)
                        ],                       
                        [
                            InlineKeyboardButton("⚠️ 𝖢𝖺𝗇'𝗍 𝖠𝖼𝖼𝖾𝗌𝗌 ❓ 𝖢𝗅𝗂𝖼𝗄 𝖧𝖾𝗋𝖾 ⚠️", url=invite_link.invite_link)
                        ]
                    ]
                )
            )
            await query.answer('Check Out The Chat',)
            await asyncio.sleep(300)
            await msg1.delete()
            await msg.delete()
            del msg1, msg
        except Exception as e:
            logger.exception(e, exc_info=True)
            await query.answer(f"Encountering Issues", True)

    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("Please Join the Channel by clicking above button & try again 🙄", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        mention = query.from_user.mention
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
                size = size
                mention = mention
        if f_caption is None:
            f_caption = f"{title}"
        if size is None:
            size = f"{size}"
        if mention is None:
            mention = f"{mention}"

        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )
    elif query.data == "pages":
        await query.answer()
        
    elif query.data == "start":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHKhilbmHnzBufARBzmu01VcJZixONQAC2QUAAgmmqFQjFkBaOSI-wCQE',
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton('➕ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘs➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                ],[
                    InlineKeyboardButton('ℹ️ ʜᴇʟᴘ', callback_data='help'),
                    InlineKeyboardButton('🔍 sᴇᴀʀᴄʜ', switch_inline_query_current_chat='')
                ],[
                    InlineKeyboardButton('MOVIES LAND', url=f'http://t.me/MoviesLandFamily')
                ],[
                    InlineKeyboardButton('🎈ᴀʙᴏᴜᴛ', callback_data='about'),
                    InlineKeyboardButton('ᴄʟᴏsᴇ🧨', callback_data='close')
                ]]
            )
        )
        await query.answer('Lᴏᴀᴅɪɴɢ..........')

        
    elif query.data == "help":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHJhilbNLEQPvPAAB4swAAdSvtkMde67fAALPBQAC-paxVB6OL83JwQQTJAQ',
            reply_markup=InlineKeyboardMarkup(
                [[
            InlineKeyboardButton('ғᴇᴀᴛᴜᴇs✨', callback_data='featuresS'),
            InlineKeyboardButton('ᴛᴏᴏʟs🛠', callback_data='toolsjns')
            ],[     
            InlineKeyboardButton('𝖡𝖺𝖼𝗄🎀', callback_data='start'),
            InlineKeyboardButton('ʜᴏᴍᴇ🏕', callback_data='start'),
            InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close_data')
            ]]
            )
        )
        await query.answer('Lᴏᴀᴅɪɴɢ..........')

    elif query.data == "about":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBGW5ii6X0yNDzQpWTW-kUm6aJobk3mwACMQQAArayWFav_0n-ZhiVESQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('📜ᴏᴘᴇɴ📜', callback_data='about_menu1')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='start'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        )
        await query.answer('ᴀʙᴏᴜᴛ.......')

    elif query.data == "about_menu1":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBGXZii63C4l4h00PyZJ7NW-KiO8Tu5AACVgIAAlgW2VUIOduo7bnwjSQE',
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton('👑 ᴅᴇᴠ 👑', callback_data='dev_dk'),
                ],
                [
                    InlineKeyboardButton('⚙️ Mᴀɪɴᴛᴀɪɴᴇᴅ Bʏ ⚙️', callback_data='jns_maintains')
                ],
                [
                    InlineKeyboardButton('🎀ʙᴀᴄᴋ🎀', callback_data='start')
                ]
                ]
            )
        )
        await query.answer('ᴀʙᴏᴜᴛ.......')
        
    elif query.data == "dev_dk":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBGXJii6mtRyOdw_xwn73fNjpiO-EqcwACjAYAAlJuWVZyrxMDtBmVryQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('🎈ᴋɪɴɢ🎈', callback_data='dev_all1'),
                        InlineKeyboardButton('📯sᴜᴘᴘᴏʀᴛ📯', url=f'https://t.me/jns_fc_bots')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='about_menu1'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        )   
    elif query.data == "dev_all1":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBH0hinPbKkK2Q1dNeMLOBxzDTaxk7XAAC5AIAAgX8WFYr5CVXDF0kuCQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('❤️‍🔥JNS❤️‍🔥', url=f'http://t.me/JINTONS')
                    ],
                    [
                        InlineKeyboardButton('🤠EVA MARIA🤠', url=f'https://t.me/TeamEvamaria')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='about_menu1'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        ) 
        
        
    elif query.data == "jns_maintains":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBGbJii8tmjG8qSOQ1veC-dUQjSdE2AwACowUAAos-YFRjIXuCWIRt3SQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('❤️‍🔥ＪƝ⟆ ᗷ〇Ƭ⟆❤️‍🔥', url=f'http://t.me/JNS_BOTS')
                    ],
                    [
                        InlineKeyboardButton('👨🏻‍🦯ᴅᴇᴠ ɴᴏᴏʙ👨🏻‍🦯', url=f'http://t.me/jintons'),
                        InlineKeyboardButton('📯sᴜᴘᴘᴏʀᴛ📯', url=f'https://t.me/jns_fc_bots')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='about_menu1'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        ) 
    elif query.data == "bros":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBGbZii8_lHTfWP78_U9HRRldy7EyA-QACKAUAAtE4WFQTdpC1zu7ZOSQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('ᴊɴs ᴍᴏᴠɪᴇ ʙᴏᴛ', url=f'http://t.me/JNSMOVIE_BOT')
                    ],
                    [
                        InlineKeyboardButton('ᴊɴs sᴇʀɪᴇs ʙᴏᴛ', url=f'https://t.me/JNS_SERIES_BOT')
                    ],                    
                    [
                        InlineKeyboardButton('ᴊɴs ɢʀᴏᴜᴘ ʜᴇʟᴘᴇʀ', url=f'https://t.me/JNS_MOVIE_BOT')
                    ],                    
                    [
                        InlineKeyboardButton('ᴊɴs ᴍᴇᴅɪᴀ sᴇᴀʀᴄʜ ʙᴏᴛ', url=f'https://t.me/Fc_media_search1_bot')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='jns_maintains'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        ) 
    elif query.data == "featuresS":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHKxilbqYZhn9DgIzNiNkorzPJFYrkwACSAUAAjSGsVTsqQZDH69WTSQE',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('⏳ғɪʟᴛᴇʀ', callback_data='filter1'),
                        InlineKeyboardButton('ᴄᴏɴɴᴇᴄᴛɪᴏɴ🧩', callback_data='coct')
                    ],
                    [
                        InlineKeyboardButton('🤐ᴍᴜᴛᴇ', callback_data='mute'),
                        InlineKeyboardButton('ʙᴀɴ🙅🏻‍♀️', callback_data='ban'),
                        InlineKeyboardButton('sᴛᴀᴛs📊', callback_data='stats')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='help'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        )
        await query.answer('ᴍᴀᴊᴏʀ ғᴇᴀᴛᴜʀᴇs..')
        
    elif query.data == "filter1":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHLBilcBy5VjoCx-eFjHhmbE5kCAarQACPAUAAm2DsFTEKVYFc4R6LSQE',
            reply_markup=InlineKeyboardMarkup(
                [[
            InlineKeyboardButton('📡ᴀᴜᴛᴏ', callback_data='autofilter'),
            InlineKeyboardButton('ᴍᴀɴᴜᴀʟ🤹🏻', callback_data='manual')
            ],[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS'),
            InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close_data')
        ]]
            )
        )
        await query.answer('ᴡᴇ ʜᴀᴠᴇ 2 ғɪʟᴛᴇʀ ᴏᴘᴛɪᴏɴs..')
        
    elif query.data == "manual":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='filter1'),
            InlineKeyboardButton('ʙᴜᴛᴛᴏɴ 🪄', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.MANUELFILTER_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer('ᴍᴀɴᴜᴀʟ ғɪʟᴛᴇʀ ᴛᴏᴏʟs.......')
        
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='manual')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ʙᴜᴛᴛᴏɴ ғᴏʀᴍᴀᴛs ʜᴇʀᴇ.................")
      
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='filter1')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.AUTOFILTER_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ᴀᴜᴛᴏғɪʟᴛᴇʀ ᴛᴏᴏʟs....")
        
    elif query.data == "stats":
        await query.answer("let i check my stats 😌")
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS'),
            InlineKeyboardButton('ʀᴇғʀᴇsʜ ♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.delete()
        await query.message.reply(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )

    elif query.data == "rfrsh":
        await query.answer("ᴀɢᴀɪɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴇᴄᴋ 😰")
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS'),
            InlineKeyboardButton('refresh♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_rfrsh_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
    elif query.data == "mute":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHIxilbNAim4GB_4YCWmNUSm_V2rmYgACHAgAArqpqVSkxS3ZZ7R8UiQE',
            reply_markup=InlineKeyboardMarkup(
                [[
            InlineKeyboardButton('🙇🏻ᴅᴇᴛᴀɪʟs', callback_data='mute_inside')
            ],[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS'),
            InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close_data')
        ]]
            )
        )
        await query.answer('ᴍᴜᴛᴇ ᴏᴘᴛɪᴏɴs....')
        
    elif query.data == "mute_inside":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.MUTE_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer('ᴏᴘᴇɴɪɴɢ ᴍᴜᴛᴇ ʜᴇʟᴘ....')
    
    elif query.data == "ban":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHIhilbM7OhUxjq4YZSeRQ7AHMmf8HgACcwUAApp7sFSnx6sXv2Xt1yQE',
            reply_markup=InlineKeyboardMarkup(
                [[
            InlineKeyboardButton('🙇🏻ᴅᴇᴛᴀɪʟs', callback_data='ban_inside')
            ],[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS'),
            InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close_data')
        ]]
            )
        )
        await query.answer('ʙᴀɴ ᴏᴘᴛɪᴏɴs....')
        
    elif query.data == "ban_inside":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.BAN_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer('ᴏᴘᴇɴɪɴɢ ʙᴀɴ ʜᴇʟᴘ....')
             
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='featuresS')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer('ᴏᴘᴇɴɪɴɢ ᴄᴏɴɴᴇᴄᴛᴏɴ ʜᴇʟᴘ..')
        
        
    elif query.data == "toolsjns":
        await query.message.delete()
        await query.message.reply_sticker(
            'CAACAgUAAxkBAAEBHLRilcElUkyCtfrlHU-FiQABrm_v2WIAAtcFAAL9hWBUGZCf0XgVQ74kBA',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('🎞 ɪᴍᴅʙ', callback_data='imbd'),
                        InlineKeyboardButton('ɪɴғᴏ 🪙', callback_data='info')
                    ],
                    [
                        InlineKeyboardButton('🗃 Cᴀʀʙᴏɴ', callback_data='carbon'),
                        InlineKeyboardButton('Uʀʟ sʜᴏʀᴛ 🔗', callback_data='urlshrt')
                    ],
                    [
                        InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='help'),
                        InlineKeyboardButton('ᴄʟᴏsᴇ💤', callback_data='close')
                    ]
                ]
            )
        )
        await query.answer('ᴍᴀᴊᴏʀ ᴛᴏᴏʟs...')
        
    elif query.data == "imbd":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='toolsjns')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.IMBD_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ɪᴍᴅʙ ᴛᴏᴏʟs........")
        
    elif query.data == "carbon":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='toolsjns')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.CARBON_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ᴛᴏᴏʟs ᴏᴘᴇɴɪɴɢ........")
        
    elif query.data == "info":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='toolsjns')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.INFO_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ᴛᴏᴏʟs ᴏᴘᴇɴɪɴɢ........")
        
    elif query.data == "urlshrt":
        buttons = [[
            InlineKeyboardButton('🎀ʙᴀᴄᴋ', callback_data='toolsjns')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.delete()
        await query.message.reply(
            text=script.SHORT_TXT,
            reply_markup=reply_markup,
            parse_mode='html',
            disable_web_page_preview=True
        )
        await query.answer("ᴛᴏᴏʟs ᴏᴘᴇɴɪɴɢ........")

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer('Piracy Is Crime')

        if status == "True" or status == "Chat":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton( 'Redirect To',
                                         callback_data=f'setgs#redirect_to#{settings["redirect_to"]}#{grp_id}',),
                    InlineKeyboardButton('👤 PM' if settings["redirect_to"] == "PM" else '📄 Chat',
                                         callback_data=f'setgs#redirect_to#{settings["redirect_to"]}#{grp_id}',),
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    elif query.data == "close":
        await query.message.delete()
    elif query.data == 'tips':
        await query.answer("=> 𝖲𝖾𝗇𝖽 𝖼𝗈𝗋𝗋𝖾𝖼𝗍 𝖬𝗈𝗏𝗂𝖾/𝗌𝖾𝗋𝗂𝖾𝗌 𝖭𝖺𝗆𝖾\n=>𝖳𝗈 𝖦𝖾𝗍 𝖡𝖾𝗍𝗍𝖾𝗋 𝗋𝖾𝗌𝗎𝗅𝗍 𝖥𝗈𝗋 movies include year and language along with movie name \n=>𝖳𝗈 𝖦𝖾𝗍 𝖡𝖾𝗍𝗍𝖾𝗋 𝗋𝖾𝗌𝗎𝗅𝗍 𝖥𝗈𝗋 𝗌𝖾𝗋𝗂𝖾𝗌 𝖤𝗀: 𝖯𝖾𝖺𝗄𝗒 𝖻𝗅𝗂𝗇𝖽𝖾𝗋𝗌 𝖲01𝖤01", True)
    elif query.data == 'moviesheading':
        await query.answer("=>This is your results, if is there any changes in result kindly follow the tips ☺️ ", True)
    elif query.data == 'filenos':
        await query.answer("=>I have only this much files 😰 \n To get more results do request as per tips 👉🏻 ", True)
    elif query.data == 'inform':
        await query.answer("⚠︎ Information ⚠︎\n\nAfter 3 minutes this message will be automatically deleted\n\nIf you do not see the requested movie / series file, look at the next page\n\n @MLDBase", True)
    try: await query.answer('Piracy Is Crime') 
    except: pass


async def auto_filter(client, msg: pyrogram.types.Message, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    
    pre = 'filep' if settings['file_secure'] else 'file'
    pre = 'Chat' if settings['redirect_to'] == 'Chat' else pre

    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                        text=f"📂 [{get_size(file.file_size)}] {file.file_name}", 
                        callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}'
                )
            ] 
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}",
                    callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}',
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f'{pre}_#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}',
                )
            ]
            for file in files
        ]

    btn.insert(0, 
        [
            InlineKeyboardButton(f'🌀 {search} 🌀', 'dupe')
        ]
    )
    btn.insert(1,
        [
            InlineKeyboardButton(f'𝖥𝗂𝗅𝖾𝗌 : {total_results}', 'dupe'),
            InlineKeyboardButton(f'𝖳𝗂𝗉𝗌', 'tips')
        ]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.message_id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"🗓 1/{round(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="NEXT ⏩", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="🗓 1/1", callback_data="pages")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            mention_bot=temp.MENTION,
            mention_user=message.from_user.mention if message.from_user else message.sender_chat.title,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>Hai 👋 {message.from_user.mention}</b> 😍\n\n<b>📁 Found ✨  Files For Your Query : {search} 👇</b> "
    if imdb and imdb.get('poster'):
        try:
            fmsg = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            fmsg = await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            fmsg = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    else:
        fmsg = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    
    await asyncio.sleep(DELETE_TIME)
    await fmsg.delete()
    await msg.delete()

    if spoll:
        await msg.message.delete()


async def advantage_spell_chok(msg):
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        k = await msg.reply("I couldn't find any movie in that name.")
        await asyncio.sleep(8)
        await k.delete()
        return
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(
        r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)',
        '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*",
                         re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match:
                gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates https://stackoverflow.com/a/7961425
    if len(gs_parsed) > 3:
        gs_parsed = gs_parsed[:3]
    if gs_parsed:
        for mov in gs_parsed:
            imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
            if imdb_s:
                movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        k = await msg.reply(" I couldn't find anything related to that. Check your spelling")
        await asyncio.sleep(8)
        await k.delete()
        return
    SPELL_CHECK[msg.message_id] = movielist
    btn = [[
        InlineKeyboardButton(
            text=movie.strip(),
            callback_data=f"spolling#{user}#{k}",
        )
    ] for k, movie in enumerate(movielist)]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'spolling#{user}#close_spellcheck')])
    zz = await msg.reply('I couldnt find anything related to that, just a sec looking for IMDB suggestions  🧐')
    await asyncio.sleep(3)
    zz1 = await zz.edit("Did you mean any one of these?  🤓",
                    reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(15)
    zz2 = await zz1.edit('check Whether it is released or not in OTT, if yes, contact @movieslandadmin_bot to add the movie in DataBase👨🏻‍💻')
    
    await asyncio.sleep(3)
    await zz2.delete()
    await msg.delete()
    
    
async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            fmsg = await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            fmsg = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        fmsg = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        fmsg = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                        
                    await asyncio.sleep(DELETE_TIME)
                    await fmsg.delete()
                    
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
