import os
import re
import statistics
from datetime import datetime, timedelta
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

from horse.constants import BASES_DIR, WEBDRIVER_PATH, ODDSCHECKER_URL, ODDSCHECKER_DIR, BETFAIR_URL, BETFAIR_DIR, \
    BBC_URL, BBC_DIR, MINUTES_INTERVAL
from horse.utils import logger
from horse.utils import prepare_bbc_dataset


def oddschecker(date_string, next_day_screen, table=False, racing_hours=False):

    if f'base_oddschecker_{date_string}_v1.csv' not in os.listdir(os.path.join(BASES_DIR, ODDSCHECKER_DIR)) or racing_hours:
        # Setting Chrome Webdriver

        # WINDOW_SIZE = "1920,1080"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--log-level=3')
        driver = webdriver.Chrome(executable_path=WEBDRIVER_PATH, chrome_options=chrome_options)
        driver.get(ODDSCHECKER_URL)
        sleep(2)

        # Skipping Ads
        try:
            ad = driver.find_elements_by_class_name('inside-close-button')
            ad[0].click()
            sleep(0.5)
        except:
            pass


        # Opening Oddschecker File
        if racing_hours:
            filename = os.path.join(BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}.csv')
            try:
                df = pd.read_csv(filename)
                table = True
            except:
                table = False


        # Tomorrow's schedule
        if next_day_screen:
            race_days = driver.find_elements_by_class_name('rs-divider')
            race_days[1].click()
            sleep(0.5)

        # country = driver.find_elements_by_class_name('race-meets')[0]
        # cities = country.find_elements_by_class_name('racing-time')

        meetings = driver.find_elements_by_class_name('race-details')
        cities = []
        for meeting in meetings:
            try:
                flag = meeting.find_element_by_class_name('flag-wrap').text
                city = meeting.find_element_by_class_name('venue').text
                if flag in ['UK', 'IRE']: # or city == 'Sam Houston':
                # if city == 'Sam Houston':
                    cities.append(meeting)
            except:
                pass

        links = []

        # Getting Races URLs
        for city in cities:
            # for race in city:
            race_links = city.find_elements_by_class_name('race-time')
            for race_link in race_links:
                link = race_link.get_property('href')

                if racing_hours:
                    time_string = link.split('/')[-2]
                    time_obj = datetime.strptime(time_string, "%H:%M")
                    time_obj = time_obj.replace(year=datetime.utcnow().year,
                                                month=datetime.utcnow().month,
                                                day=datetime.utcnow().day)

                    if datetime.utcnow() + timedelta(minutes=1) < time_obj <= datetime.utcnow() + timedelta(minutes=MINUTES_INTERVAL + 1):
                        links.append(link)

                    # if datetime.utcnow().minute < 32:
                    #     if hour == datetime.utcnow().hour and minutes > 34:
                    #         links.append(link)
                    # else:
                    #     if hour == datetime.utcnow().hour + 1:
                    #         links.append(link)
                else:
                    links.append(link)

        # Extracting Odds of each race
        logger.warning(f'Oddschecker: Consultando {len(links)} corridas')

        if len(links):
            count = len(links)
            for link in links:

                # Selenium opening page
                driver.get(link)
                sleep(1.5)

                # Skipping Ads
                try:
                    ad = driver.find_elements_by_class_name('choose-uk')
                    ad[0].click()
                    sleep(0.5)
                except:
                    pass
                try:
                    ad = driver.find_elements_by_class_name('webpush-swal2-close')
                    ad[0].click()
                    sleep(0.5)
                except:
                    pass
                try:
                    ad = driver.find_elements_by_class_name('js-close-class')
                    ad[0].click()
                    sleep(0.5)
                except:
                    pass

                city = link.split('/')[-3]
                if str(city).startswith('2021'):
                    city = " ".join(city.split('-')[3:])
                else:
                    city = city.replace('-', ' ')

                time = link.split('/')[-2]

                lines = driver.find_elements_by_class_name('diff-row')
                horses_race = len(lines)
                non_runners = 0
                for i, line in enumerate(lines):
                    started = i + 1

                    # Selenium
                    horse = line.find_element_by_css_selector('a').text.strip().replace("'", "")
                    if len(horse.split("(")) > 1:
                        horse = horse.split("(")[0].strip()
                    odd_columns = line.find_elements_by_css_selector('td')[2:]

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

                    if table:
                        df = df.append({
                            'date': date_string,
                            'time': time,
                            'city': city,
                            'horse': horse,
                            'started': started,
                            'oddschecker': odd_mean,
                            'odd_list': odd_list
                        }, ignore_index=True)
                    else:
                        df = pd.DataFrame({
                            'date': [date_string],
                            'time': [time],
                            'city': [city],
                            'horse': [horse],
                            'started': [started],
                            'oddschecker': [odd_mean],
                            'odd_list': [odd_list]
                        })
                        table = True

                count -= 1
                logger.warning(f'Oddschecker: Faltam {count} corridas')

            df = df.drop_duplicates(subset=['date', 'time', 'city', 'horse'], keep='last')

            if racing_hours:
                filename = os.path.join(BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}.csv')
                df.to_csv(filename, index=False)
            else:
                filename = os.path.join(BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}_v1.csv')
                df.to_csv(filename, index=False)
        else:

            logger.warning(f'Oddschecker: Sem corridas entre {datetime.utcnow().strftime("%H:%M")}'
                            f' e {(datetime.utcnow() + timedelta(minutes=MINUTES_INTERVAL)).strftime("%H:%M")}')

        return driver, len(links)
    return None, 0


def betfair(date_string, next_day_screen, table=False, racing_hours=False, driver=None):
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

        driver.get(BETFAIR_URL)
        sleep(10)

        if racing_hours:
            filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}.csv')
            try:
                df = pd.read_csv(filename)
                table = True
            except:
                table = False


        # Accept Cookies Screen
        try:
            driver.find_elements_by_id('onetrust-accept-btn-handler')[0].click()
            sleep(1)
        except Exception as e:
            pass


        if next_day_screen:
            driver.find_elements_by_class_name('schedule-filter-button')[1].click()
            sleep(1.5)
        # else:
        #     driver.find_elements_by_class_name('schedule-filter-button')[0].click()


        country_content = driver.find_elements_by_class_name('country-content')
        meetings = country_content[0].find_elements_by_class_name('meeting-item')

        timetable = []
        for meeting in meetings:
            city = meeting.find_element_by_class_name('meeting-label').text.lower()
            going = meeting.find_element_by_class_name('racetrack-conditions').text.lower()
            race_times = meeting.find_elements_by_class_name('race-link')

            meeting_timetable = []
            for race_time in race_times:
                if racing_hours:
                    time_string = race_time.text
                    time_obj = datetime.strptime(time_string, "%H:%M")
                    time_obj = time_obj.replace(year=datetime.now().year,
                                                month=datetime.now().month,
                                                day=datetime.now().day)

                    if datetime.now() + timedelta(minutes=1) < time_obj <= datetime.now() + timedelta(minutes=MINUTES_INTERVAL + 1):
                        meeting_timetable.append(race_time.get_property('href'))

                else:
                    meeting_timetable.append(race_time.get_property('href'))

            if meeting_timetable:
                timetable.append((city, going, meeting_timetable))

        count = sum([len(i[2]) for i in timetable])
        logger.warning(f'Betfair: Consultando {count} corridas')

        if count > 0:
            for item in timetable:
                links = item[2]
                for link in links:
                    driver.get(link)

                    sleep(5)
                    event_info = driver.find_elements_by_class_name('event-info')[0]

                    time = event_info.find_element_by_class_name('venue-name').text.split()[0]
                    hour = int(time.split(":")[0])

                    hour_us = datetime.now().hour
                    hour_uk = datetime.utcnow().hour

                    if hour_us > hour_uk:
                        hour_uk += 24

                    time = (datetime.strptime(time, '%H:%M') + timedelta(hours=hour_uk-hour_us)).strftime('%H:%M')

                    city = event_info.find_element_by_class_name('venue-name').text.split()[1:]
                    city = " ".join(city).lower()

                    race_type = event_info.find_element_by_class_name('market-name').text
                    lines = driver.find_elements_by_class_name('runner-line')
                    horses_race = len(lines)
                    for line in lines:
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

                        for i, timeform_horse in enumerate(timeform_horses):
                            horse_name = timeform_horse.text.split('(')[0].strip().replace("'", "")
                            if horse == horse_name:
                                horse_timeform = i + 1

                        if table:
                            df = df.append({
                                'date': date_string,
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
                        else:
                            df = pd.DataFrame({
                                'date': [date_string],
                                'time': [time],
                                'city': [city],
                                'going': [item[1].split('(')[0].strip()],
                                'horses_race': [horses_race],
                                'horse': [horse],
                                'jockey': [jockey],
                                'betfair_back': [betfair_back],
                                'betfair_lay': [betfair_lay],
                                'race_type': [race_type],
                                'timeform': [horse_timeform]
                            })
                            table = True
                    count -= 1
                    logger.warning(f'Betfair: Faltam {count} corridas')

            df['horse'] = df['horse'].str.replace("'", "")

            df = df.drop_duplicates(subset=['date', 'time', 'city', 'horse', 'horses_race'], keep='last')

            if racing_hours:
                filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}.csv')
                df.to_csv(filename, index=False)
            else:
                filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}_v1.csv')
                df.to_csv(filename, index=False)
        else:
            logger.warning(f'Betfair: Sem corridas entre {datetime.utcnow().strftime("%H:%M")}'
                            f' e {(datetime.utcnow() + timedelta(minutes=MINUTES_INTERVAL)).strftime("%H:%M")}')

def bbc(date_string, table=False, force=False):
    df_bbc_full = pd.read_csv(os.path.join(BASES_DIR, 'base_bbc_full.csv'),
                              parse_dates=['date'])

    filename = os.path.join(BASES_DIR, BBC_DIR, f'base_bbc_{date_string}.csv')

    today = datetime.now().strftime('%Y.%m.%d')
    if f'base_bbc_{date_string}.csv' not in os.listdir(os.path.join(BASES_DIR, BBC_DIR)) or today == date_string:
        force = True
    else:
        if 'title' not in pd.read_csv(os.path.join(BASES_DIR, BBC_DIR, f'base_bbc_{date_string}.csv')):
            # TODO Change do True when refining the model
            force = True

    if force:
        logger.warning(f'Consultando BBC para o dia {date_string}')
        date_url = datetime.strptime(date_string, '%Y.%m.%d').strftime('%Y-%m-%d')

        # Accessing BBC's Website
        rq = requests.session()
        rq = rq.get(f'{BBC_URL}{date_url}')
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
                date_file = title_content[-1].text.replace('th', '').replace('st', '').replace('nd', '').replace('rd','').replace('Augu', 'August')
                date_file = datetime.strptime(date_file, '%d %B %Y').strftime('%Y.%m.%d')
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

                logger.warning(f"Apparently the link {link} hasn't loaded properly")
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
                        df = df.append({
                            'date': date_file,
                            'time': time,
                            'city': city,
                            'finished': finished,
                            'horse': horse,
                            'jockey': jockey,
                            'trainer': trainer,
                            'odds': oddschecker,
                            'horse_age': horse_age,
                            'horse_weight': horse_weight,
                            'gap': gap,
                            'title': race_title,
                            'going': race_going,
                            'horses_race': race_horses,
                            'distance': race_distance
                        }, ignore_index=True)
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
                    logger.warning(f'Corrida {city} - {time} finalizada, mas resultados não carregados')

    else:
        logger.warning(f'Carregando arquivo BBC para o dia {date_string}')
        df = pd.read_csv(filename, parse_dates=['date'])
        table = False

    if table:
        df.drop_duplicates(subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
        if 'winner' not in df:
            df = prepare_bbc_dataset(df, df_bbc_full)

            # df = df[['time', 'city', 'horse', 'distance', 'going', 'title', 'horses_race']]
            # df_old = pd.read_csv(filename)
            # df_old.drop(columns=['horses_race', 'time'], inplace=True)
            # df_join = pd.merge(df_old, df, how='left', on=['city', 'horse'])

        df.to_csv(filename, index=False)

        logger.warning(f'Arquivo {filename} salvo!')

        logger.warning('Updating BBC Full')

        df_bbc_full = df_bbc_full.append(df)
        df_bbc_full.drop_duplicates(subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
        df_bbc_full.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
        df_bbc_full.to_csv(os.path.join(BASES_DIR, 'base_bbc_full.csv'), index=False)
    else:
        logger.warning(f'Aparentemente nao houve corridas no dia {date_string}')
