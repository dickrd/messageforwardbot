import datetime
import os
from threading import Thread

import itchat
from itchat.content import *
from telegram.utils import helpers

from module.base import Module, Friend


class WechatModule(Module):

    def __init__(self, bot):
        self.bot = bot

        self.file_path = "file/wechat/"
        try:
            os.makedirs(self.file_path)
        except OSError:
            pass

        self.wechat_id = None

    def login(self):
        itchat.auto_login(hotReload=True, enableCmdQR=2)

        friends = itchat.update_friend(update=True)
        friend_list = []
        for friend in friends:
            the_friend = WechatFriend(friend)
            if not self.bot.is_conflict("wechat", the_friend.channel):
                friend_list.append(("wechat", the_friend.name, the_friend.channel))
        self.bot.update_friend_list(friend_list)
        self.wechat_id = itchat.search_friends()['UserName']
        Thread(target=itchat.run).start()

    def get_friend(self, channel):
        return WechatFriend(itchat.search_friends(userName=channel))

    @itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING, PICTURE, RECORDING, ATTACHMENT, VIDEO])
    def forward(self, msg):
        if msg['FromUserName'] == self.wechat_id:
            return

        if msg.type in [PICTURE, RECORDING, ATTACHMENT, VIDEO]:
            _, ext = os.path.splitext(msg.fileName)
            file_path = os.path.join(self.file_path, "{0}{1}".format(datetime.datetime.now().timestamp(), ext))
            msg.download(file_path)
            content = self.bot.base_url.format(file_path)
        else:
            content = helpers.escape_markdown(msg['Content'].encode('utf-8'))

        self.bot.send(WechatFriend(msg['User']), content)


class WechatFriend(Friend):
    def __init__(self, user):
        channel = user['UserName'].encode('utf-8')
        if 'RemarkName' in user and len(user['RemarkName']) > 0:
            name = user['RemarkName'].encode('utf-8')
        elif 'NickName' in user and len(user['NickName']) >= 0:
            name = user['NickName'].encode('utf-8')
        else:
            name = channel

        super(WechatFriend, self).__init__("wechat", name, channel)
        self.user = user

    def send(self, message):
        self.user.send(message)
