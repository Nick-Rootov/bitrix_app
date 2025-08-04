# Пример local_settings
# Измените данные на свои

DEBUG = True
ALLOWED_HOSTS = ['*']

from integration_utils.bitrix24.local_settings_class import LocalSettingsClass

TINKOFF_API_KEY = 'your-api-key'
ENDPOINT_TINKOFF = 'your-secret-key'
API_KEY_TINKOFF = 'your-api-key'
SECRET_KEY_TINKOFF = 'your-secret-key'
NGROK_URL = 'http://localhost:8000'
OPEN_AI_API_KEY = 'your-api-key'


APP_SETTINGS = LocalSettingsClass(
    portal_domain='b24-67nbhl.bitrix24.ru',
    app_domain='localhost:8000',
    app_name='is-demo',
    salt='asdasdasdwdsdfgsdvdfgrsgdrgdfgSADfsdvsdfsdSFSDfsvdfsefscVVSDVSEsfsdfsdvsse',
    secret_key='adasdasdasdasdasdwdgbnbnntgdfd.sdfsvdfgsdf.dfgbdfdgdfg',
    application_bitrix_client_id='local.6889e148483c15.44209758',
    application_bitrix_client_secret='eFcQpMyxaqVkJ21hMW8ytX2prjJTq9qZekt6PHq9US0DB9g8Py',
    application_index_path='/',
)

DOMAIN = "56218ef983f3-8301993767665431593.ngrok-free.app"
#DOMAIN = "127.0.0.1:8000"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'is_demo',  # Or path to database file if using sqlite3.
        'USER': 'is_demo',  # Not used with sqlite3.
        'PASSWORD': ',2p2l2yys[2025',  # Not used with sqlite3.
        'HOST': 'localhost',
        'PORT': '5432',
    },
}