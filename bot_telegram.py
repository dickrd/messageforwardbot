# -*- coding: utf-8 -*-
import sqlite3
import time

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils import helpers

from module.base import System
from module.wechat import WechatModule


class TelegramBot(object):

    def __init__(self, db_path, base_url, service_list):
        self.db_path = db_path
        self.base_url = base_url

        self.ttl = 1000 * 60 * 5

        self.last = None
        self.last_active = None
        self.active_sender = {}
        self.own_account = set()

        self.service = {}
        for service in service_list:
            self.login(service)

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("select value from config where key = 'telegram_token';")
        token = cursor.fetchone()[0]

        cursor.execute("select value from config where key = 'telegram_chat_id';")
        self.chat_id = int(cursor.fetchone()[0])
        connection.close()

        self.updater = Updater(token=token)
        self.updater.dispatcher.add_handler(CommandHandler('claim', self.claim))
        self.updater.dispatcher.add_handler(CommandHandler('friends', self.friend_list))
        self.updater.dispatcher.add_handler(CommandHandler('to', self.to_friend))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.forward))

    def generate_text(self, sender, message):
        if sender == System():
            return message

        if sender.friend_id == -1:
            self.update_friend_list([(sender.service, sender.name, sender.channel)])

            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("select friend_id from friend where service = ? and channel = ?;",
                                (sender.service, sender.channel))
            sender.friend_id = int(cursor.fetchone()[0])
            connection.close()

        now = int(round(time.time() * 1000))
        if not self.last or sender != self.last or self.last_active + self.ttl < now:
            self.last = sender
            self.last_active = now
            return "`{0}#{1:04}`\n{3}".format(sender.name.encode('utf-8'), sender.friend_id, sender.channel.encode('utf-8'), message)
        else:
            return message

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    def send(self, sender, message):
        if sender.friend_id == -1:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("select friend_id from friend where service = ? and name = ?;", (sender.service, sender.name))
            row = cursor.fetchone()
            if not row:
                cursor.execute("insert into friend(service, name, channel) values(?, ?, ?);", (sender.service, sender.name, sender.channel))
                connection.commit()
                cursor.execute("select friend_id from friend where service = ? and name = ?;", (sender.service, sender.name))
                row = cursor.fetchone()

            sender.friend_id = row[0]
            connection.close()

        if not sender in self.own_account:
            self.active_sender[sender] = int(round(time.time() * 1000))
        self.updater.bot.send_message(chat_id=self.chat_id,
                                      parse_mode='Markdown',
                                      text=self.generate_text(sender, message))

    def login(self, service):
        if service == "wechat":
            self.service["wechat"] = WechatModule(self)
            self.own_account.add(self.service["wechat"].login())
        else:
            print("unsupported service: {0}".format(service))

    def update_friend_list(self, friends):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        for item in friends:
            cursor.execute("select count(*) from friend where service = ? and name = ?;", (item[0], item[1]))
            if cursor.fetchone()[0] > 0:
                cursor.execute("update friend set channel = ? where service = ? and name = ?;", (item[2], item[0], item[1]))
                continue

            cursor.execute("select count(*) from friend where service = ? and channel = ?;", (item[0], item[2]))
            if cursor.fetchone()[0] > 0:
                cursor.execute("update friend set name = ? where service = ? and channel = ?;", (item[1], item[0], item[2]))
                continue

            cursor.execute("insert into friend(service, name, channel) values(?, ?, ?);", item)
        connection.commit()
        connection.close()

    def claim(self, bot, update):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("select value from config where key == 'claim_secret';")
        secret = cursor.fetchone()[0]

        if update.message.text.replace('/claim', '').strip() == secret:
            cursor.execute("update config set value = ? where key = 'telegram_chat_id';", (update.message.chat_id,))
            connection.commit()
            connection.close()
            self.chat_id = update.message.chat_id
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`claim successful`"))
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`claim failed\nusage:\n/claim <secret>`"))

    def to_friend(self, bot, update):
        lines = update.message.text.split("\n", 1)
        # noinspection PyBroadException
        try:
            friend_id = int(lines[0].replace('/to', '').strip())
        except Exception:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`syntax error\nusage:\n/to <friend_id>\n<message_body>`"))
            return

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("select service, channel from friend where friend_id == ?;", (friend_id,))
        row = cursor.fetchone()

        if not row:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`no friend with id: {0}`".format(friend_id)))
            return

        friend = self.service[row[0]].get_friend(row[1])
        friend.friend_id = friend_id

        if len(lines) == 2:
            friend.send(lines[1])
        self.active_sender[friend] = int(round(time.time() * 1000))

    def friend_list(self, bot, update):
        if update.message.chat_id != self.chat_id:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`no claim`"))
            return

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("select friend_id, service, name from friend;")
        friends = cursor.fetchall()
        connection.close()
        message = ""
        for row in friends:
            message += "{0:04}  {1}  {2}\n".format(row[0], row[1], row[2].encode('utf-8'))

        message = self.generate_text(System(), helpers.escape_markdown(message))

        buf = ""
        for line in message.split("\n"):
            if len(buf + "\n" + line) < 1024:
                buf = buf + "\n" + line
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text="`{0}`".format(buf.strip('\n')))
                buf = line
        bot.send_message(chat_id=update.message.chat_id,
                         parse_mode='Markdown',
                         text="`{0}`".format(buf.strip('\n')))

    def forward(self, bot, update):
        if update.message.chat_id != self.chat_id:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`no claim`"))
            return

        content = update.message.text
        current_active = {}
        now = int(round(time.time() * 1000))
        for sender in self.active_sender:
            if self.active_sender[sender] + self.ttl > now:
                current_active[sender] = self.active_sender[sender]
        self.active_sender = current_active

        if len(current_active) == 1:
            for k in current_active:
                k.send(content)
                self.active_sender[k] = now

        elif len(current_active) > 1:
            keyboard = []
            for k in current_active:
                keyboard.append([InlineKeyboardButton("{0}#{1:03}".format(k.name.encode('utf-8'), k.friend_id),
                                                      callback_data=str(k.friend_id))])

            keyboard.append([InlineKeyboardButton("[cancel]", callback_data="-1")])

            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "{0}\n`will be send to:`".format(content.encode('utf-8'))),
                             reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "`no recipient`"))

    def callback(self, bot, update):
        friend_id = int(update.callback_query.data)
        if friend_id == -1:
            update.callback_query.edit_message_text(parse_mode='Markdown',
                             text=self.generate_text(System(), "`not sent`"))
        else:
            lines = update.callback_query.message.text.split('\n')
            content = '\n'.join(lines[:-1])

            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("select service, channel, name from friend where friend_id == ?;", (friend_id,))
            row = cursor.fetchone()

            if not row:
                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text=self.generate_text(System(), "`no friend with id: {0}`".format(friend_id)))
                update.callback_query.answer()
                return

            friend = self.service[row[0]].get_friend(row[1])
            friend.friend_id = friend_id
            friend.send(content)
            self.active_sender[friend] = int(round(time.time() * 1000))

            update.callback_query.edit_message_text(parse_mode='Markdown',
                                                    text=self.generate_text(System(), "`sent {0}#{1:04}`".format(helpers.escape_markdown(row[2].encode('utf-8')), friend_id)))

        update.callback_query.edit_message_reply_markup()
        update.callback_query.answer()
