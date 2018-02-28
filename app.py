import threading

import itchat
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters

config = {
    'telegram_chat_id': -1,
    'telegram_bot_token': '563612637:AAGCKFEoCm_zcye9AEVXyQFF1Otikajmils'
}

import logging
logging.basicConfig(format='[%(asctime)s - %(name)s - %(levelname)s]\t%(message)s',
                    level=logging.INFO)

@itchat.msg_register(itchat.content.TEXT, isGroupChat=False, isFriendChat=True)
def wechat_forward_text(msg):
    if config['telegram_chat_id'] == -1:
        return

    keyboard = [[InlineKeyboardButton("Reply", switch_inline_query_current_chat=msg['FromUserName'])]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    updater.bot.send_message(chat_id=config['telegram_chat_id'],
                             text='{0}: \n{1}'.format(msg['FromUserName'], msg['Text']),
                             reply_markup=reply_markup)

def telegram_register(bot, update):
    config['telegram_chat_id'] = update.message.chat_id
    bot.send_message(chat_id=update.message.chat_id, text="Auth completed.")

def telegram_forward_reply(bot, update):
    contents = update.message.text.split(' ', maxsplit=2)
    recipient = itchat.search_friends(userName=contents[0])[0]
    recipient.send(text=contents[1])

itchat.auto_login(hotReload=True, enableCmdQR=2)
itchat_thread = threading.Thread(target=itchat.run)


updater = Updater(token=config['telegram_bot_token'])
reply_handler = MessageHandler(Filters.all, telegram_forward_reply)
start_handler = CommandHandler('0x3c1f', telegram_register)
updater.dispatcher.add_handler(reply_handler)
updater.dispatcher.add_handler(start_handler)
telegram_thread = threading.Thread(target=updater.start_polling)

itchat_thread.start()
telegram_thread.start()
