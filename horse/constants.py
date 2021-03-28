# FOLDERS
import os

# LINUX
BASES_DIR = f'{os.path.expanduser("~")}/Projects/sportsbet/horse/bases'
MODELOS_DIR = f'{os.path.expanduser("~")}/Projects/sportsbet/horse/modelos'
TEMPLATES_DIR = f'{os.path.expanduser("~")}/Projects/sportsbet/horse/templates'
WEBDRIVER_PATH = os.path.realpath(os.path.join(BASES_DIR, 'chromedriver'))

# WINDOWS
# BASES_DIR = r'H:\sportsbet\horse\bases'
# MODELOS_DIR = r'H:\sportsbet\horse\modelos'
# TEMPLATES_DIR = r'H:\sportsbet\horse\templates'
# WEBDRIVER_PATH = r'H:\sportsbet\horse\chromedriver.exe'

ATTHERACE_DIR = '0_attherace'
ODDSCHECKER_DIR = '1_oddschecker'
BETFAIR_DIR = '2_betfair'
ODDFAIR_DIR = '3_betfair+oddschecker'
BETS_DIR = '4_palpites'
BBC_DIR = '5_bbc'
BBC_PICKLE_DIR = '5_bbc_pickle'
DAILY_BASES_DIR = '6_bases_diarias'
HISTORICAL_BASES_DIR = '7_bases_historicas'
BETS_RESULT_DIR = '8_palpites+bbc'
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

MINUTES_INTERVAL = 2
RACING_HOURS = range(6, 21)

# MAILING LIST
# FINANCE_MAIL_LIST = []
FINANCE_MAIL_LIST = ['timigoandroid@gmail.com', 'rlouroa@hotmail.com', 'me@alexandresalem.com']

