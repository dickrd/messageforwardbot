import sqlite3

from bot_telegram import TelegramBot


def _main():
    db_path = "message.db"
    base_url = "http://bot.hehehey.com/{0}"
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("select count(*) from sqlite_master where type='table' and name='config';")
    if cursor.fetchone()[0] == 0:
        print("==> init database...")
        token = raw_input("token:  ")
        secret = raw_input("secret: ")
        cursor.execute("create table config "
                       "("
                       "  key   text,"
                       "  value text,"
                       "  primary key (key)"
                       ");")
        cursor.execute("create table friend"
                       "("
                       "  friend_id integer,"
                       "  service   text,"
                       "  channel   text,"
                       "  name      text,"
                       "  primary key (friend_id autoincrement)"
                       ");")
        for item in [("claim_secret", secret), ("telegram_token", token), ("telegram_chat_id", "-1")]:
            cursor.execute("insert into config(key, value) values (?, ?);", item)
        connection.commit()
        connection.close()
    print("==> starting bot...")
    bot = TelegramBot(db_path, base_url, ["wechat"])
    bot.start()

_main()
