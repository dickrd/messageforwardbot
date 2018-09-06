import datetime

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from module.base import System
from module.wechat import WechatModule


class TelegramBot(object):

    def __init__(self, cursor, base_url, service_list):
        self.cursor = cursor
        self.base_url = base_url

        self.ttl = 60 * 2

        self.last = None
        self.active_sender = {}

        self.service = {}
        for service in service_list:
            self.login(service)

        self.cursor.execute("select value from config where key = 'telegram_token';")
        token = self.cursor.fetchone()[0]

        self.cursor.execute("select value from config where key = 'telegram_chat_id';")
        self.chat_id = self.cursor.fetchone()[0]

        self.updater = Updater(token=token)
        self.updater.dispatcher.add_handler(CommandHandler('claim', self.claim))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.forward))

        self.update_friend_list([("system", "system", "system",)])

    def generate_text(self, sender, message):
        if sender.friend_id == -1:
            if not self.is_conflict(sender.service, sender.channel):
                self.update_friend_list([(sender.service, sender.name, sender.channel)])
            self.cursor.execute("select friend_id from friend where service = ? and channel = ?;",
                                (sender.service, sender.channel))
            sender.friend_id = self.cursor.fetchone()[0]

        if not self.last or sender != self.last:
            self.last = sender
            return '`{0}#{1:03} *{2}*`\n{3}'.format(sender.name, sender.friend_id, sender.channel, message)
        else:
            return message

    def start(self):
        self.updater.start_polling()

    def send(self, sender, message):
        self.active_sender[sender] = datetime.datetime.now().timestamp()
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
        self.cursor.executeMany("replace into friend(service, name, channel) values(?, ?, ?);", friends)
        self.cursor.commit()

    def is_conflict(self, service, channel):
        self.cursor.execute("select count(*) from friend where service = ? and channel = ?;", (service, channel))
        return self.cursor.fetchone()[0] > 0

    def claim(self, bot, update):
        self.cursor.execute("select value from config where key == 'claim_secret';")
        secret = self.cursor.fetchone()[0]

        if '/claim ' + secret == update.message.text:
            self.cursor.execute("update config set value = ? where key = 'telegram_chat_id';", (update.message.chat_id,))
            self.cursor.commit()
            self.chat_id = update.message.chat_id
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "\tclaim successful"))
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "\tclaim failed\n\tusage:\n\t/claim <secret>"))

    def forward(self, bot, update):
        if update.message.chat_id != self.chat_id:
            bot.send_message(chat_id=update.message.chat_id,
                             parse_mode='Markdown',
                             text=self.generate_text(System(), "\tno claim"))
            return

        if update.message.reply_to_message:
            parts = update.message.reply_to_message.text.split('\n', 1)
            if len(parts) == 2:
                # TODO implement forward
                pass
        else:
            current_active = []
            now = datetime.datetime.now().timestamp()
            for sender, timestamp in self.active_sender:
                if timestamp + self.ttl > now:
                    current_active[sender] = timestamp
            self.active_sender = current_active

            if len(current_active) == 1:
                for k in current_active:
                    current_active[k].send(update.message.text)

            elif len(current_active) > 1:
                keyboard = []
                count = 0
                for k in current_active:
                    if count > 3:
                        break
                    keyboard.append([InlineKeyboardButton("{0}#{1:03}".format(current_active[k].name, current_active[k].friend_id),
                                                          callback_data=str(current_active[k].friend_id))])
                    count += 1

                keyboard.append([InlineKeyboardButton("cancel", callback_data="-1")])

                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text=self.generate_text(System(), "\tchoose a recipient"),
                                 reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 parse_mode='Markdown',
                                 text=self.generate_text(System(), "\tno recipient"))
