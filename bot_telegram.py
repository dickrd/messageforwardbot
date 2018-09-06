# -*- coding: utf-8 -*-
import sqlite3
import time

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from module.base import System
from module.wechat import WechatModule


class TelegramBot(object):

    def __init__(self, db_path, base_url, service_list):
        self.db_path = db_path
        self.base_url = base_url

        self.ttl = 1000 * 60 * 2

        self.last = None
        self.active_sender = {}

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
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.forward))

    def generate_text(self, sender, message):
        if sender.friend_id == -1:
            if not self.is_conflict(sender.service, sender.channel):
                self.update_friend_list([(sender.service, sender.name, sender.channel)])

            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("select friend_id from friend where service = ? and channel = ?;",
                                (sender.service, sender.channel))
            sender.friend_id = int(cursor.fetchone()[0])
            connection.close()

        if not self.last or sender != self.last:
            self.last = sender
            return "`{0}#{1:03}`\n{3}".format(sender.name.encode('utf-8'), sender.friend_id, sender.channel.encode('utf-8'), message)
        else:
            return message

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    def send(self, sender, message):
        self.active_sender[sender] = int(round(time.time() * 1000))
        self.updater.bot.send_message(chat_id=self.chat_id,
                                      parse_mode='Markdown',
                                      text=self.generate_text(sender, message))

    def login(self, service):
        if service == "wechat":
            self.service["wechat"] = WechatModule(self)
            self.service["wechat"].login()
        else:
            print("unsupported service: {0}".format(service))

    def update_friend_list(self, friends):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        for item in friends:
            cursor.execute("replace into friend(service, name, channel) values(?, ?, ?);", item)
        connection.commit()
        connection.close()

    def is_conflict(self, service, channel):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("select count(*) from friend where service = ? and channel = ?;", (service, channel))
            return cursor.fetchone()[0] > 0

    def claim(self, bot, update):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("select value from config where key == 'claim_secret';")
        secret = cursor.fetchone()[0]

        if '/claim ' + secret == update.message.text:
            cursor.execute("update config set value = ? where key = 'telegram_chat_id';", (update.message.chat_id,))
            connection.commit()
            connection.close()
            self.chat_id = update.message.chat_id
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "claim successful"))
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "claim failed\nusage:\n/claim <secret>"))

    def forward(self, bot, update):
        if update.message.chat_id != self.chat_id:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "no claim"))
            return

        if update.message.reply_to_message:
            parts = update.message.reply_to_message.text.split('\n', 1)
            if len(parts) == 2:
                # TODO implement forward
                pass
        else:
            current_active = {}
            now = int(round(time.time() * 1000))
            for sender in self.active_sender:
                if self.active_sender[sender] + self.ttl > now:
                    current_active[sender] = self.active_sender[sender]
            self.active_sender = current_active

            if len(current_active) == 1:
                for k in current_active:
                    k.send(update.message.text)

            elif len(current_active) > 1:
                keyboard = []
                count = 0
                for k in current_active:
                    if count > 3:
                        break
                    keyboard.append([InlineKeyboardButton("{0}#{1:03}".format(k.name.encode('utf-8'), k.friend_id),
                                                          callback_data=str(k.friend_id))])
                    count += 1

                keyboard.append([InlineKeyboardButton("cancel", callback_data="-1")])

                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text=self.generate_text(System(), "choose a recipient"),
                                 reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text=self.generate_text(System(), "no recipient"))
