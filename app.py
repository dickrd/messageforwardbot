import json
import threading

import itchat
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters

config = None
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    if 'telegram_bot_prefix' not in config \
            or 'telegram_bot_token' not in config \
            or 'telegram_chat_id' not in config:
        raise IOError
except IOError:
    print('Read config.json failed.')
    exit(-1)

@itchat.msg_register(itchat.content.INCOME_MSG, isFriendChat=True)
def wechat_forward_text(msg):
    if config['telegram_chat_id'] == -1:
        print('Telegram not ready.')
        return

    if 'User' not in msg or 'FromUserName' not in msg:
        print('No user from wechat.\n----DUMP----\n{0}\n----END----'.format(msg))
        return
    if msg['FromUserName'] == itchat.search_friends()['UserName']:
        print('Skip wechat message sent by self.')
        return

    if 'RemarkName' in msg['User'] and len(msg['User']['RemarkName']) > 0:
        name = msg['User']['RemarkName'].encode('utf-8')
    elif 'NickName' in msg['User'] and len(msg['User']['NickName']) >= 0:
        name = msg['User']['NickName'].encode('utf-8')
    else:
        name = msg['User']['UserName'].encode('utf-8')

    if msg.type != itchat.content.TEXT:
        content = msg.type
    else:
        content = msg['Content'].encode('utf-8')

    keyboard = [[InlineKeyboardButton("Reply", switch_inline_query_current_chat='@' + name + ' ')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    updater.bot.send_message(chat_id=config['telegram_chat_id'],
                             text='`{0}`{1}'.format(name, content),
                             parse_mode='Markdown',
                             reply_markup=reply_markup)

def telegram_register(bot, update):
    if config['telegram_chat_id'] != -1:
        bot.send_message(chat_id=config['telegram_chat_id'],
                         parse_mode='Markdown',
                         text="`Disconnected`")

    config['telegram_chat_id'] = update.message.chat_id
    try:
        with open('config.json', 'w') as the_config_file:
            json.dump(config, the_config_file)
    except IOError:
        print('Write config.json failed.')

    bot.send_message(chat_id=update.message.chat_id,
                     parse_mode='Markdown',
                     text="`Connected`")

def telegram_forward_text(bot, update):
    text = update.message.text[1:]
    if text.startswith(config['telegram_bot_prefix']):
        text = text[len(config['telegram_bot_prefix']):]

    contents = text.split(' ', 1)
    if len(contents) != 2:
        bot.send_message(chat_id=update.message.chat_id,
                         parse_mode='Markdown',
                         text="`Incompatible Message({0})`".format(len(contents)))
        return

    friend = itchat.search_friends(name=contents[0])
    if len(friend) == 1:
        friend[0].send(contents[1])
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         parse_mode='Markdown',
                         text="`Unspecific Recipient({0})`".format(len(friend)))

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
