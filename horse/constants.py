# FOLDERS
import os

# LINUX
BASES_DIR = os.path.join(os.path.expanduser(
    "~"), 'Projects', 'sports_bet', 'horse', 'bases')
MODELOS_DIR = os.path.join(os.path.expanduser(
    "~"), 'Projects', 'sports_bet', 'horse', 'modelos')
TEMPLATES_DIR = os.path.join(os.path.expanduser(
    "~"), 'Projects', 'sports_bet', 'horse', 'templates')
WEBDRIVER_PATH = os.path.join(os.path.expanduser(
    "~"), 'Projects', 'sports_bet', 'horse', 'chromedriver.exe')

# WINDOWS
# BASES_DIR = r'H:\sportsbet\horse\bases'
# MODELOS_DIR = r'H:\sportsbet\horse\modelos'
# TEMPLATES_DIR = r'H:\sportsbet\horse\templates'
# WEBDRIVER_PATH = r'H:\sportsbet\horse\chromedriver.exe'

ATTHERACE_DIR = '0_attherace'
RACES_LINK_DIR = '0_races_link'
ODDSCHECKER_DIR = '1_oddschecker'
BETFAIR_DIR = '2_betfair'
ODDFAIR_DIR = '3_betfair_oddschecker'
BETS_DIR = '4_palpites'
BBC_DIR = '5_bbc'
BBC_PICKLE_DIR = '5_bbc_pickle'
DAILY_BASES_DIR = '6_bases_diarias'
HISTORICAL_BASES_DIR = '7_bases_historicas'
BETS_RESULT_DIR = '8_palpites_bbc'
FINANCEIRO_DIR = '9_financeiro'

# SCRAPPER
ODDSCHECKER_URL = 'https://www.oddschecker.com/horse-racing/'
BETFAIR_URL = 'https://www.betfair.com/exchange/plus/en/horse-racing-betting-7'
BBC_URL = 'https://www.bbc.com/sport/horse-racing/uk-ireland/results/'
RACINGTV_URL = 'https://www.racingtv.com/search?utf8=%E2%9C%93&query='

# MODELS
CONSERVADOR = 2
MEDIANO = 4
AGRESSIVO = 8

MINUTES_INTERVAL = 3
RACING_HOURS = range(12, 21)

TELEGRAM_API_KEY = "5640169397:AAH0u2mlh8I-UcVKQutRw8zztvLyDAZ8pcg"

# MAILING LIST
# FINANCE_MAIL_LIST = []
FINANCE_MAIL_LIST = ['me@alexandresalem.com']
