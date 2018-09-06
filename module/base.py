class Module(object):
    def login(self):
        raise NotImplementedError()
    def get_friend(self, friend_id):
        raise NotImplementedError()

class Friend(object):
    def __init__(self, service, name, channel, friend_id=-1):
        self.friend_id = friend_id
        self.service = service
        self.name = name
        self.channel = channel

    def __eq__(self, o):
        if isinstance(o, self.__class__):
            return self.service == o.service and self.channel == o.channel
        else:
            return False

    def __ne__(self, o):
        return not self.__eq__(o)

    def __hash__(self):
        return hash((self.service, self.channel))

    def send(self, message):
        raise NotImplementedError()

class System(Friend):
    def __init__(self):
        super(System, self).__init__("system", "system", "system")
    def send(self, message):
        pass
