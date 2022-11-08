from logging import debug
import pandas as pd
from time import sleep
import horse.constants as const

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common import desired_capabilities

from horse.utils import logger
import os


class Betfair():
    def __init__(self) -> None:
        self.df_betfair = pd.DataFrame(columns=['date',
                                                'time',
                                                'city',
                                                'going',
                                                'horses_race',
                                                'horse',
                                                'jockey',
                                                'betfair_back',
                                                'betfair_lay',
                                                'race_type',
                                                'timeform'])

    def _get_betfair_links(self, execution_period):
        self.driver.get(const.BETFAIR_URL)

        sleep(10)

        # Accept Cookies Screen
        try:
            self.driver.find_elements_by_id('onetrust-accept-btn-handler')[0].click()
            sleep(1)
        except Exception as e:
            pass

        if execution_period=="d1":
            self.driver.find_elements_by_class_name('schedule-filter-button')[1].click()
            sleep(6.5)
        # else:
        #     driver.find_elements_by_class_name('schedule-filter-button')[0].click()

        country_content = self.driver.find_elements_by_class_name('country-content')
        meetings = country_content[0].find_elements_by_class_name('meeting-item')

        timetable = []
        for meeting in meetings:
            city = meeting.find_element_by_class_name('meeting-label').text.lower()
            going = meeting.find_element_by_class_name('racetrack-conditions').text.lower()
            meeting_races = meeting.find_elements_by_class_name('race-link')


            meeting_timetable = []
            
            for meeting_race in meeting_races:
                link = meeting_race.get_property('href')
                print(link)
                race_time = 1

            
                self.links[f'{city} - {race_time}'] = {'oddschecker': link}
            if meeting_timetable:
                timetable.append((city, going, meeting_timetable))

    def _betfair(date_string, next_day_screen, table=False, racing_hours=False, driver=None):
        if f'base_betfair_{date_string}_v1.csv' not in os.listdir(os.path.join(BASES_DIR, BETFAIR_DIR)) or racing_hours:
            if not driver:
                # WINDOW_SIZE = "1920,1080"
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                # chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
                # chrome_options.add_argument('--no-sandbox')
                caps = DesiredCapabilities().CHROME
                # caps["pageLoadStrategy"] = "normal"  # Waits for full page load
                caps["pageLoadStrategy"] = "none"
                driver = webdriver.Chrome(desired_capabilities=caps, executable_path=WEBDRIVER_PATH, chrome_options=chrome_options)

            

            count = sum([len(i[2]) for i in timetable])
            logger.warning(f'Betfair: Consultando {count} corridas')

            df = pd.DataFrame(columns=['date',
                                    'time',
                                    'city',
                                    'going',
                                    'horses_race',
                                    'horse',
                                    'jockey',
                                    'betfair_back',
                                    'betfair_lay',
                                    'race_type',
                                    'timeform'])
            if racing_hours:
                ext = ""
                filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')
                try:
                    df = df.append(pd.read_csv(filename))
                except:
                    logger.warning("Criando arquivo Betfair com a primeira corrida do dia")
            else:
                ext = "_v1"
                filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')

            if f"{date_string}{ext}" not in os.listdir(os.path.join(BASES_DIR, BETFAIR_DIR)):
                os.mkdir(os.path.join(BASES_DIR, BETFAIR_DIR, f"{date_string}{ext}"))

            if count > 0:
                for item in timetable:
                    links = item[2]

                    threads = []
                    for link in links:

                        t = threading.Thread(target=scrap_betfair, args=(link, df, date_string, item, ext, ))
                        t.start()
                        threads.append(t)

                    for thread in threads:
                        thread.join()

                    count -= len(threads)
                    logger.info(f'Betfair: Faltam {count} corridas')

                    threads.clear()

                df = pd.concat([pd.read_csv(os.path.join(BASES_DIR,
                                                        BETFAIR_DIR,
                                                        f'{date_string}{ext}',
                                                        file), parse_dates=['date']) for file in os.listdir(os.path.join(BASES_DIR, BETFAIR_DIR, f"{date_string}{ext}"))],
                                            axis=0,
                                            join='inner').sort_values(by=['date', 'city', 'time'])
                df['horse'] = df['horse'].str.replace("'", "")
                df = df.drop_duplicates(subset=['date', 'time', 'city', 'horse', 'horses_race'], keep='last')

                df.to_csv(filename, index=False)

            else:
                logger.warning(f'Betfair: Sem corridas entre {datetime.utcnow().strftime("%H:%M")}'
                                f' e {(datetime.utcnow() + timedelta(minutes=MINUTES_INTERVAL)).strftime("%H:%M")}')



def _scrap_betfair(self, link, filename):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        caps = DesiredCapabilities().CHROME
        caps["pageLoadStrategy"] = "normal"  # Waits for full page load
        # caps["pageLoadStrategy"] = "none"
        driver = webdriver.Chrome(desired_capabilities=caps, executable_path=const.WEBDRIVER_PATH, chrome_options=chrome_options)

        driver.get(link)
        sleep(15)

        event_info = driver.find_elements_by_class_name('event-info')[0]
        time = event_info.find_element_by_class_name('venue-name').text.split()[0]
        
        # hour = int(time.split(":")[0])

        hour_us = datetime.now().hour
        hour_uk = self.race_date.hour

        if hour_us > hour_uk:
            hour_uk += 24

        time = (datetime.strptime(time, '%H:%M') + timedelta(hours=hour_uk - hour_us)).strftime('%H:%M')

        city = event_info.find_element_by_class_name('venue-name').text.split()[1:]
        city = " ".join(city).lower()

        race_type = event_info.find_element_by_class_name('market-name').text
        lines = driver.find_elements_by_class_name('runner-line')

        horses_race = len(lines)
        for i, line in enumerate(lines):
            try:
                horse = line.find_element_by_class_name('runner-name').text
            except Exception as e:
                horse = ''
            try:
                jockey = line.find_element_by_class_name('jockey-name').text
            except Exception as e:
                jockey = ''

            try:
                odds = line.find_elements_by_class_name('mv-bet-button-info')
            except Exception as e:
                odds = []

            if odds:
                betfair_back = odds[2].find_element_by_css_selector('span').text
                betfair_lay = odds[3].find_element_by_css_selector('span').text
            else:
                betfair_back = 999
                betfair_lay = 999
                horses_race -= 1

            timeform_horses = []
            horse_timeform = ''
            try:
                timeform = driver.find_elements_by_class_name('runner-rating-list')[0]
                timeform_horses = timeform.find_elements_by_css_selector('li p')
            except Exception as e:
                logger.warning(f'Timeform não encontrado: {city}: {time}')

            for j, timeform_horse in enumerate(timeform_horses):
                horse_name = timeform_horse.text.split('(')[0].strip().replace("'", "")
                if horse == horse_name:
                    horse_timeform = j + 1

            self.df_betfair = self.df_betfair.append({
                'date': self.race_date_string,
                'time': time,
                'city': city,
                'going': item[1].split('(')[0].strip(),
                'horses_race': horses_race,
                'horse': horse,
                'jockey': jockey,
                'betfair_back': betfair_back,
                'betfair_lay': betfair_lay,
                'race_type': race_type,
                'timeform': horse_timeform
            }, ignore_index=True)

        df.to_csv(os.path.join(BASES_DIR, BETFAIR_DIR, f"{date_string}{ext}", f"betfair_{city}_{time}.csv"), index=False)

        driver.close()


