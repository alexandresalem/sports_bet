import os
import re
import statistics
import threading
from datetime import datetime, timedelta
from time import sleep
import pytz
import json

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import horse.constants as const
from horse.utils import logger
from horse.utils import prepare_bbc_dataset


class WebDriver():
    """ Setting Chrome Webdriver """

    @staticmethod
    def get_driver(headless=False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        else:
            WINDOW_SIZE = "1920,1080"
            chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--log-level=3')
            user_agent = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'AppleWebKit/537.36 (KHTML, like Gecko)' 'Chrome/96.0.4664.45' 'Safari/537.36')
            chrome_options.add_argument(f'user-agent={user_agent}')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument(
                '--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])

        driver = webdriver.Chrome(
            executable_path=const.WEBDRIVER_PATH, chrome_options=chrome_options)

        return driver


class Oddschecker():
    def __init__(self):
        self.date_us = datetime.now()
        self.date_uk = datetime.utcnow().replace(
            tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/London"))

    def _skip_adds(self):
        # Skipping Ads
        try:
            ad = self.driver.find_elements(
                by=By.CLASS_NAME, value='inside-close-button')
            ad[0].click()
            sleep(0.5)
        except:
            pass

    def get_race_times(self):
        # Tomorrow's schedule
        self.driver = WebDriver.get_driver()
        self.driver.get(const.ODDSCHECKER_URL)
        self._skip_adds()
        if self.date_uk.day == self.date_us.day:
            race_days = self.driver.find_elements(
                by=By.CLASS_NAME, value='rs-divider')
            race_days[1].click()
            sleep(0.5)

        meetings = self.driver.find_elements(
            by=By.CLASS_NAME, value='race-details')
        races = []
        for meeting in meetings:
            try:
                flag = meeting.find_element(
                    by=By.CLASS_NAME, value='flag-wrap').text
                if flag in ['UK', 'IRE']:  # or city == 'Sam Houston':
                    # if city == 'Sam Houston':
                    races.append(meeting)
            except:
                pass

        race_times = {}
        # Getting Races URLs
        for race in races:
            # for race in city:
            race_links = race.find_elements(
                by=By.CLASS_NAME, value='race-time')
            city = race.find_element(
                by=By.CLASS_NAME, value='venue').text
            for race_link in race_links:
                link = race_link.get_property('href')
                race_time = link.split('/')[-2]
                race_times[race_time] = (city, link)

        with open(os.path.join(const.BASES_DIR, const.RACES_LINK_DIR, self.race_times_file), "w") as race_file:
            json.dump(race_times, race_file)
        self.driver.close()
        return race_times

    def is_racing_hours(self):
        racing_hours = [datetime.strptime(race_time, "%H:%M").replace(year=self.date_uk.year,
                                                                      month=self.date_uk.month,
                                                                      day=self.date_uk.day,
                                                                      tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/London")) for race_time in sorted(self.race_times.keys())]

        return self.date_uk + timedelta(minutes=const.MINUTES_INTERVAL) > racing_hours[0] and self.date_uk < racing_hours[-1]

    def scrap(self, race_day=False):
        self.race_times_file = f'races_{self.date_uk.strftime("%Y.%m.%d")}.json'
        if self.race_times_file not in os.listdir(os.path.join(const.BASES_DIR, const.RACES_LINK_DIR)):
            self.race_times = self.get_race_times()
            self.racing_hours = False
        else:
            with open(os.path.join(
                    const.BASES_DIR, const.RACES_LINK_DIR, self.race_times_file), "r") as race_file:
                self.race_times = json.load(race_file)
                self.racing_hours = self.is_racing_hours()

                if self.racing_hours:
                    number_races = len(self.race_times)
                    for k, v in self.race_times.items():
                        race_time = datetime.strptime(k, "%H:%M")
                        race_time_uk = race_time.replace(year=self.date_uk.year,
                                                         month=self.date_uk.month,
                                                         day=self.date_uk.day,
                                                         tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/London"))
                        race_time_br = race_time.replace(year=self.date_uk.year,
                                                         month=self.date_uk.month,
                                                         day=self.date_uk.day,
                                                         tzinfo=pytz.utc).astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M")
                        if (race_time_uk - self.date_uk).seconds <= (60 * const.MINUTES_INTERVAL) and self.date_uk < race_time_uk:
                            self.race_times = {k: v}
                            self.send_telegram_message(
                                f"*{v[0]}: {race_time_br} (BR) - {k} (UK)* \nComecando a rodar algoritmo para sugestao de apostas")
                            break
                    if len(self.race_times) == number_races:
                        raise Exception(
                            f'Nao há corridas entre: {self.date_uk.strftime("%H:%M")} e {(self.date_uk + timedelta(minutes=const.MINUTES_INTERVAL)).strftime("%H:%M")}')

        logger.info(
            f'Oddschecker: Consultando {len(self.race_times)} corridas')

        ext = "_v0" if self.racing_hours else "_v1"
        filename = os.path.join(
            const.BASES_DIR, const.ODDSCHECKER_DIR, f'base_oddschecker_{self.date_uk.strftime("%Y.%m.%d")}{ext}.csv')

        if self.racing_hours and os.path.exists(filename):
            self.df = pd.read_csv(filename)
        else:
            self.df = pd.DataFrame(columns=['date',
                                            'time',
                                            'city',
                                            'horse',
                                            'horses_race',
                                            'started',
                                            'oddschecker',
                                            'odd_list'])

        count = len(self.race_times)
        for race_time, (city, link) in self.race_times.items():
            self.scrap_race(link, ext)
            count -= 1
            logger.info(f'Oddschecker: Faltam {count} corridas')
            self.df = self.df.sort_values(by=['date', 'city', 'time'])

            self.df = self.df.drop_duplicates(
                subset=['date', 'time', 'city', 'horse'], keep='last')

            self.df.to_csv(filename, index=False)

    def scrap_race(self, link, ext):
        # chrome_options = Options()
        # # chrome_options.add_argument("--headless")
        # WINDOW_SIZE = "1920,1080"
        # chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--log-level=3')
        # caps = DesiredCapabilities().CHROME
        # caps["pageLoadStrategy"] = "normal"  # Waits for full page load
        # # caps["pageLoadStrategy"] = "none"
        # driver = webdriver.Chrome(
        #     desired_capabilities=caps, executable_path=const.WEBDRIVER_PATH, chrome_options=chrome_options)
        self.driver = WebDriver.get_driver()
        # Selenium opening page
        self.driver.get(link)
        sleep(1.5)

        # Skipping Ads
        try:
            ad = self.driver.find_elements(by=By.CLASS_NAME, value='choose-uk')
            ad[0].click()
            sleep(0.5)
        except:
            pass
        try:
            ad = self.driver.find_elements(
                by=By.CLASS_NAME, value='webpush-swal2-close')
            ad[0].click()
            sleep(0.5)
        except:
            pass
        try:
            ad = self.driver.find_elements(
                by=By.CLASS_NAME, value='js-close-class')
            ad[0].click()
            sleep(0.5)
        except:
            pass

        city = link.split('/')[-3]
        if str(city).startswith('2022'):
            city = " ".join(city.split('-')[3:])
        else:
            city = city.replace('-', ' ')

        time = link.split('/')[-2]

        lines = self.driver.find_elements(by=By.CLASS_NAME, value='diff-row')
        horses_race = len(lines)
        non_runners = 0
        for i, line in enumerate(lines):
            started = i + 1

            # Selenium
            horse = line.find_element(
                By.CSS_SELECTOR, 'a').text.strip().replace("'", "")
            if len(horse.split("(")) > 1:
                horse = horse.split("(")[0].strip()
            odd_columns = line.find_elements(By.CSS_SELECTOR, 'td')[2:-7]

            odd_list = []
            for odd_column in odd_columns:
                odd_text = odd_column.text.split('/')
                # Se for fracao
                if len(odd_text) == 2:
                    try:
                        odd = round(int(odd_text[0]) / int(odd_text[1]), 2)
                        odd_list.append(odd)
                    except Exception as e:
                        pass

                # Se for numero inteiro
                elif len(odd_text) == 1:
                    try:
                        odd = int(odd_text[0])
                        odd_list.append(odd)
                    except Exception as e:
                        pass

            if non_runners > 0:
                started -= 1

            if odd_list:
                odd_mean = round(statistics.mean(odd_list), 2)
            else:
                odd_mean = ""
                started = horses_race - non_runners
                non_runners += 1
                pass

            new_row = pd.Series({
                'date': self.date_uk.strftime('%Y.%m.%d'),
                'time': time,
                'city': city,
                'horse': horse,
                'horses_race': horses_race,
                'started': started,
                'oddschecker': odd_mean,
                'odd_list': odd_list
            })

            self.df = pd.concat(
                [self.df, new_row.to_frame().T], ignore_index=True)
        self.driver.close()


# def betfair(date_string, next_day_screen, table=False, racing_hours=False, driver=None):
#     if f'base_betfair_{date_string}_v1.csv' not in os.listdir(os.path.join(const.BASES_DIR, const.BETFAIR_DIR)) or racing_hours:
#         if not driver:
#             WINDOW_SIZE = "1920,1080"
#             chrome_options = Options()
#             # chrome_options.add_argument("--headless")
#             chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
#             chrome_options.add_argument('--no-sandbox')
#             caps = DesiredCapabilities().CHROME
#             # caps["pageLoadStrategy"] = "normal"  # Waits for full page load
#             caps["pageLoadStrategy"] = "none"
#             driver = webdriver.Chrome(
#                 desired_capabilities=caps, executable_path=const.WEBDRIVER_PATH, chrome_options=chrome_options)

#         driver.get(BETFAIR_URL)

#         sleep(10)

#         # Accept Cookies Screen
#         try:
#             driver.find_elements(
#                 by=By.ID, value='onetrust-accept-btn-handler')[0].click()
#             sleep(1)
#         except Exception as e:
#             pass

#         if next_day_screen:
#             driver.find_elements(
#                 by=By.CLASS_NAME, value='schedule-filter-button')[1].click()
#             sleep(1.5)
#         # else:
#         #     driver.find_elements(by=By.CLASS_NAME, value='schedule-filter-button')[0].click()

#         country_content = driver.find_elements(
#             by=By.CLASS_NAME, value='country-content')
#         meetings = country_content[0].find_elements(
#             by=By.CLASS_NAME, value='meeting-item')

#         timetable = []
#         for meeting in meetings:
#             city = meeting.find_element(
#                 by=By.XPATH, value='meeting-label').text.lower()
#             going = meeting.find_element(
#                 by=By.CLASS_NAME, value='racetrack-conditions').text.lower()
#             race_times = meeting.find_elements(
#                 by=By.CLASS_NAME, value='race-link')

#             meeting_timetable = []
#             for race_time in race_times:
#                 if racing_hours:
#                     time_string = race_time.text
#                     time_obj = datetime.strptime(time_string, "%H:%M")
#                     time_obj = time_obj.replace(year=datetime.now().year,
#                                                 month=datetime.now().month,
#                                                 day=datetime.now().day)

#                     if datetime.now() + timedelta(minutes=1) < time_obj <= datetime.now() + timedelta(minutes=MINUTES_INTERVAL + 1):
#                         meeting_timetable.append(
#                             race_time.get_property('href'))

#                 else:
#                     meeting_timetable.append(race_time.get_property('href'))

#             if meeting_timetable:
#                 timetable.append((city, going, meeting_timetable))

#         count = sum([len(i[2]) for i in timetable])
#         logger.warning(f'Betfair: Consultando {count} corridas')

#         df = pd.DataFrame(columns=['date',
#                                    'time',
#                                    'city',
#                                    'going',
#                                    'horses_race',
#                                    'horse',
#                                    'jockey',
#                                    'betfair_back',
#                                    'betfair_lay',
#                                    'race_type',
#                                    'timeform'])
#         if racing_hours:
#             ext = ""
#             filename = os.path.join(
#                 BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')
#             try:
#                 df = df.append(pd.read_csv(filename))
#             except:
#                 logger.warning(
#                     "Criando arquivo Betfair com a primeira corrida do dia")
#         else:
#             ext = "_v1"
#             filename = os.path.join(
#                 BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')

#         if f"{date_string}{ext}" not in os.listdir(os.path.join(BASES_DIR, BETFAIR_DIR)):
#             os.mkdir(os.path.join(
#                 BASES_DIR, BETFAIR_DIR, f"{date_string}{ext}"))

#         if count > 0:
#             for item in timetable:
#                 links = item[2]

#                 threads = []
#                 for link in links:

#                     t = threading.Thread(target=scrap_betfair, args=(
#                         link, df, date_string, item, ext, ))
#                     t.start()
#                     threads.append(t)

#                 for thread in threads:
#                     thread.join()

#                 count -= len(threads)
#                 logger.info(f'Betfair: Faltam {count} corridas')

#                 threads.clear()

#             df = pd.concat([pd.read_csv(os.path.join(BASES_DIR,
#                                                      BETFAIR_DIR,
#                                                      f'{date_string}{ext}',
#                                                      file), parse_dates=['date']) for file in os.listdir(os.path.join(BASES_DIR, BETFAIR_DIR, f"{date_string}{ext}"))],
#                            axis=0,
#                            join='inner').sort_values(by=['date', 'city', 'time'])
#             df['horse'] = df['horse'].str.replace("'", "")
#             df = df.drop_duplicates(
#                 subset=['date', 'time', 'city', 'horse', 'horses_race'], keep='last')

#             df.to_csv(filename, index=False)

#         else:
#             logger.warning(f'Betfair: Sem corridas entre {datetime.utcnow().strftime("%H:%M")}'
#                            f' e {(datetime.utcnow() + timedelta(minutes=MINUTES_INTERVAL)).strftime("%H:%M")}')


# def scrap_betfair(link, df, date_string, item, ext):
#     chrome_options = Options()
#     chrome_options.add_argument("--headless")
#     caps = DesiredCapabilities().CHROME
#     caps["pageLoadStrategy"] = "normal"  # Waits for full page load
#     # caps["pageLoadStrategy"] = "none"
#     driver = webdriver.Chrome(
#         desired_capabilities=caps, executable_path=WEBDRIVER_PATH, chrome_options=chrome_options)

#     driver.get(link)
#     sleep(15)

#     event_info = driver.find_elements(by=By.CLASS_NAME, value='event-info')[0]
#     time = event_info.find_element(
#         by=By.CLASS_NAME, value='venue-name').text.split()[0]
#     hour = int(time.split(":")[0])

#     hour_us = datetime.now().hour
#     hour_uk = datetime.utcnow().hour

#     if hour_us > hour_uk:
#         hour_uk += 24

#     time = (datetime.strptime(time, '%H:%M') +
#             timedelta(hours=hour_uk - hour_us)).strftime('%H:%M')

#     city = event_info.find_element(
#         by=By.CLASS_NAME, value='venue-name').text.split()[1:]
#     city = " ".join(city).lower()

#     race_type = event_info.find_element(
#         by=By.CLASS_NAME, value='market-name').text
#     lines = driver.find_elements(by=By.CLASS_NAME, value='runner-line')

#     horses_race = len(lines)
#     for i, line in enumerate(lines):
#         try:
#             horse = line.find_element(
#                 by=By.CLASS_NAME, value='runner-name').text
#         except Exception as e:
#             horse = ''
#         try:
#             jockey = line.find_element(
#                 by=By.CLASS_NAME, value='jockey-name').text
#         except Exception as e:
#             jockey = ''

#         try:
#             odds = line.find_elements(
#                 by=By.CLASS_NAME, value='mv-bet-button-info')
#         except Exception as e:
#             odds = []

#         if odds:
#             betfair_back = odds[2].find_element(By.CSS_SELECTOR, 'span').text
#             betfair_lay = odds[3].find_element(By.CSS_SELECTOR, 'span').text
#         else:
#             betfair_back = 999
#             betfair_lay = 999
#             horses_race -= 1

#         timeform_horses = []
#         horse_timeform = ''
#         try:
#             timeform = driver.find_elements(
#                 by=By.CLASS_NAME, value='runner-rating-list')[0]
#             timeform_horses = timeform.find_elements(By.CSS_SELECTOR, 'li p')
#         except Exception as e:
#             logger.warning(f'Timeform não encontrado: {city}: {time}')

#         for j, timeform_horse in enumerate(timeform_horses):
#             horse_name = timeform_horse.text.split(
#                 '(')[0].strip().replace("'", "")
#             if horse == horse_name:
#                 horse_timeform = j + 1

#         df = df.append({
#             'date': date_string,
#             'time': time,
#             'city': city,
#             'going': item[1].split('(')[0].strip(),
#             'horses_race': horses_race,
#             'horse': horse,
#             'jockey': jockey,
#             'betfair_back': betfair_back,
#             'betfair_lay': betfair_lay,
#             'race_type': race_type,
#             'timeform': horse_timeform
#         }, ignore_index=True)

#     df.to_csv(os.path.join(BASES_DIR, BETFAIR_DIR,
#               f"{date_string}{ext}", f"betfair_{city}_{time}.csv"), index=False)

#     driver.close()


def bbc(date_string, table=False, force=False):
    df_bbc_full = pd.read_csv(os.path.join(const.BASES_DIR, 'base_bbc_full.csv'),
                              parse_dates=['date'])

    filename = os.path.join(const.BASES_DIR, const.BBC_DIR,
                            f'base_bbc_{date_string}.csv')

    today = datetime.now().strftime('%Y.%m.%d')
    if f'base_bbc_{date_string}.csv' not in os.listdir(os.path.join(const.BASES_DIR, const.BBC_DIR)) or today == date_string:
        force = True
    else:
        if 'title' not in pd.read_csv(os.path.join(const.BASES_DIR, const.BBC_DIR, f'base_bbc_{date_string}.csv')):
            # TODO Change do True when refining the model
            force = True

    if force:
        logger.warning(f'Consultando BBC para o dia {date_string}')
        date_url = datetime.strptime(
            date_string, '%Y.%m.%d').strftime('%Y-%m-%d')

        # Accessing BBC's Website
        rq = requests.session()
        rq = rq.get(f'{const.BBC_URL}{date_url}')
        page = rq.content
        soup = BeautifulSoup(page, 'lxml')
        columns = soup.find_all('td', re.compile('gs-o-table__cell'))

        # Getting Races URLs
        links = []
        for column in columns:
            if column.text == "Full result":
                link = column.find('a')['href']
                links.append(f'https://www.bbc.com{link}')

        table = False
        df = None
        for link in links:
            rq = requests.get(link)
            page = rq.content
            soup = BeautifulSoup(page, 'lxml')
            title = soup.find('h1', re.compile('gel-trafalgar'))
            try:
                title_content = title.find_all('span')

                city = title_content[0].text.lower()
                date_file = title_content[-1].text.replace('th', '').replace(
                    'st', '').replace('nd', '').replace('rd', '').replace('Augu', 'August')
                date_file = datetime.strptime(
                    date_file, '%d %B %Y').strftime('%Y.%m.%d')
                time = soup('button', re.compile('sp-c-filter-nav__link'))
                time = time[1].text
                # time = time.split(':')
                # time = round(int(time[0]) + (int(time[1]) / 60), 1)
                race_title = soup('h3', re.compile('qa-title'))[0].text
                race_going = soup('dd', re.compile('qa-going'))[0].text
                race_distance = soup('dd', re.compile('qa-distance'))[0].text
                race_horses = soup('dd', re.compile('qa-runners'))[0].text

                columns = soup('td', re.compile('gs-o-table__cell'))
            except Exception as e:

                logger.warning(
                    f"Apparently the link {link} hasn't loaded properly")
                logger.warning(e)
                pass

            for i in range(0, len(columns), 8):
                try:
                    finished = columns[i].text.split()[0]
                    horse = columns[i + 1].text.replace("'", "")
                    oddschecker = columns[i + 2].text
                    horse_age = columns[i + 3].text
                    horse_weight = columns[i + 4].text
                    gap = columns[i + 5].text
                    trainer = columns[i + 6].text
                    jockey = columns[i + 7].text

                    if table:
                        df2 = pd.DataFrame({
                            'date': [date_file],
                            'time': [time],
                            'city': [city],
                            'finished': [finished],
                            'horse': [horse],
                            'jockey': [jockey],
                            'trainer': [trainer],
                            'odds': [oddschecker],
                            'horse_age': [horse_age],
                            'horse_weight': [horse_weight],
                            'gap': [gap],
                            'title': [race_title],
                            'going': [race_going],
                            'horses_race': [race_horses],
                            'distance': [race_distance]
                        })
                        df = pd.concat([df, df2], ignore_index=True)
                    else:
                        df = pd.DataFrame({
                            'date': [date_file],
                            'time': [time],
                            'city': [city],
                            'finished': [finished],
                            'horse': [horse],
                            'jockey': [jockey],
                            'trainer': [trainer],
                            'odds': [oddschecker],
                            'horse_age': [horse_age],
                            'horse_weight': [horse_weight],
                            'gap': [gap],
                            'title': [race_title],
                            'going': [race_going],
                            'horses_race': [race_horses],
                            'distance': [race_distance]
                        })
                        table = True
                except:
                    logger.warning(
                        f'Corrida {city} - {time} finalizada, mas resultados não carregados')

    else:
        logger.warning(f'Carregando arquivo BBC para o dia {date_string}')
        df = pd.read_csv(filename, parse_dates=['date'])
        table = False

    if table:
        df.drop_duplicates(
            subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
        if 'winner' not in df:
            df = prepare_bbc_dataset(df, df_bbc_full)

            # df = df[['time', 'city', 'horse', 'distance', 'going', 'title', 'horses_race']]
            # df_old = pd.read_csv(filename)
            # df_old.drop(columns=['horses_race', 'time'], inplace=True)
            # df_join = pd.merge(df_old, df, how='left', on=['city', 'horse'])

        df.to_csv(filename, index=False)

        logger.warning(f'Arquivo {filename} salvo!')

        logger.warning('Updating BBC Full')

        df_bbc_full = pd.concat([df_bbc_full, df])
        df_bbc_full.drop_duplicates(
            subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
        df_bbc_full.sort_values(
            by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
        df_bbc_full.to_csv(os.path.join(
            const.BASES_DIR, 'base_bbc_full.csv'), index=False)
    else:
        logger.warning(
            f'Aparentemente nao houve corridas no dia {date_string}')
