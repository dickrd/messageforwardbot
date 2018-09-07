import os
import time
from threading import Thread

import itchat
from itchat.content import *
from telegram.utils import helpers

from module.base import Module, Friend

wechat = None


class WechatModule(Module):

    def __init__(self, bot):
        global wechat
        wechat = self

        self.bot = bot

        self.file_path = "file/"
        try:
            os.makedirs(self.file_path)
        except OSError:
            pass

    def login(self):
        itchat.auto_login(hotReload=True, enableCmdQR=2)

        friends = itchat.get_friends(update=True)
        friend_list = []
        for friend in friends:
            the_friend = WechatFriend(friend)
            friend_list.append(("wechat", the_friend.name, the_friend.channel))
        self.bot.update_friend_list(friend_list)
        Thread(target=itchat.run).start()

    def get_friend(self, channel):
        return WechatFriend(itchat.search_friends(userName=channel))


class WechatFriend(Friend):
    def __init__(self, user):
        channel = user['UserName']
        if 'RemarkName' in user and len(user['RemarkName']) > 0:
            name = user['RemarkName']
        elif 'NickName' in user and len(user['NickName']) >= 0:
            name = user['NickName']
        else:
            name = channel

        super(WechatFriend, self).__init__("wechat", name, channel)
        self.user = user

    def send(self, message):
        self.user.send(message)


@itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING, PICTURE, RECORDING, ATTACHMENT, VIDEO])
def forward(msg):
    if msg.type in [PICTURE, RECORDING, ATTACHMENT, VIDEO]:
        _, ext = os.path.splitext(msg.fileName)
        file_path = os.path.join(wechat.file_path, "{0}{1}".format(int(round(time.time() * 1000)), ext))
        msg.download(file_path)
        content = wechat.bot.base_url.format(file_path)
    else:
        content = helpers.escape_markdown(msg['Content'].encode('utf-8'))

    wechat.bot.send(wechat.get_friend(msg['FromUserName']), content)
