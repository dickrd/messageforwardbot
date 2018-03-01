import threading

import itchat
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters

config = {
    'telegram_bot_prefix': 'MessageForwardBot @',
    'telegram_chat_id': -1,
    'telegram_bot_token': '563612637:AAGCKFEoCm_zcye9AEVXyQFF1Otikajmils'
}

import logging
logging.basicConfig(format='[%(asctime)s - %(name)s - %(levelname)s]\t%(message)s',
                    level=logging.ERROR)

@itchat.msg_register(itchat.content.INCOME_MSG, isGroupChat=False)
def wechat_forward_text(msg):
    if config['telegram_chat_id'] == -1:
        print('Telegram not ready.')
        return

    if 'User' not in msg:
        print('No user in wechat message: {0}'.format(msg))
        return
    if 'RemarkName' not in msg['User'] or len(msg['User']['RemarkName']) == 0:
        name = '@{0}'.format(msg['User']['NickName'].encode('utf-8'))
    else:
        name = '@{0}'.format((msg['User']['RemarkName'].encode('utf-8')))

    keyboard = [[InlineKeyboardButton("Reply", switch_inline_query_current_chat=name + ' ')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    updater.bot.send_message(chat_id=config['telegram_chat_id'],
                             text='{0}\n{1}'.format(name, msg['Content'].encode('utf-8')),
                             reply_markup=reply_markup)

def telegram_register(bot, update):
    config['telegram_chat_id'] = update.message.chat_id
    bot.send_message(chat_id=update.message.chat_id,
                     text="[Initialization Completed]")

def telegram_forward_text(bot, update):
    text = update.message.text[1:]
    if text.startswith(config['telegram_bot_prefix']):
        text = text[len(config['telegram_bot_prefix']):]

    contents = text.split(' ', 1)
    if len(contents) != 2:
        bot.send_message(chat_id=update.message.chat_id,
                         text="[Incompatible Message({0})]".format(len(contents)))
        return

    friend = itchat.search_friends(name=contents[0])
    if len(friend) == 1:
        friend[0].send(contents[1])
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text="[Unspecific Recipient({0})]".format(len(friend)))

itchat.auto_login(hotReload=True, enableCmdQR=2)
itchat_thread = threading.Thread(target=itchat.run)

updater = Updater(token=config['telegram_bot_token'])
start_handler = CommandHandler('0x3c1f', telegram_register)
updater.dispatcher.add_handler(start_handler)
reply_handler = MessageHandler(Filters.text, telegram_forward_text)
updater.dispatcher.add_handler(reply_handler)
telegram_thread = threading.Thread(target=updater.start_polling)

itchat_thread.start()
telegram_thread.start()
