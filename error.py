import os
from decouple import config, UndefinedValueError
import pytz

class Config:
    try:
        API_ID = config('API_ID', cast=int)
        API_HASH = config('API_HASH')
        BOT_TOKEN = config('BOT_TOKEN')
        PHONE_NUMBER = config('PHONE_NUMBER')
        USER_GROUP_ID = config('USER_GROUP_ID', cast=int)
        TARGET_USER_IDS = [int(id.strip()) for id in config('TARGET_USER_IDS').split(',') if id.strip().isdigit()]
        NOTIFICATION_TARGET = config('NOTIFICATION_TARGET', cast=int)
        TIMEZONE = pytz.timezone('US/Pacific')
    except UndefinedValueError as e:
        print(f"Environment variable not set: {e}")
        raise