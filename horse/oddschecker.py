import pandas as pd
from time import sleep

import statistics

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common import desired_capabilities
import horse.constants as const

class Oddschecker():
    def __init__(self) -> None:
        self.df_oddschecker = df = pd.DataFrame(columns=['date',
                                                        'time',
                                                        'city',
                                                        'horse',
                                                        'started',
                                                        'oddschecker',
                                                        'odd_list'])


    def _open_oddschecker_home(self):
        self.driver.get(const.ODDSCHECKER_URL)
        sleep(5)

        # Skipping Ads
        try:
            ad = self.driver.find_elements_by_class_name('inside-close-button')
            ad[0].click()
            sleep(1.5)
        except:
            pass
    
    def _get_oddschecker_links(self, execution_period):
        self._open_oddschecker_home()
        # Tomorrow's screen

        if execution_period=='d1':
            sleep(2.5)
            race_days = self.driver.find_elements_by_class_name('rs-divider')
            self.driver.execute_script("arguments[0].click();", race_days[1])
            sleep(0.5)

        self.links = {}
        meetings = filter(lambda meeting: meeting.find_element_by_class_name('flag-wrap').text in ['UK', 'IRE'], self.driver.find_elements_by_class_name('race-details'))
        for meeting in meetings:
            flag = meeting.find_element_by_class_name('flag-wrap').text
            city = meeting.find_element_by_class_name('venue').text.lower()
            
            race_links = meeting.find_elements_by_class_name('race-time')
            for race_link in race_links:
                link = race_link.get_property('href')
                race_time = link.split('/')[-2]
                self.links[f'{city} - {race_time}'] = {'oddschecker': link}


    def _scrap_oddschecker(self, link, filename):
        chrome_options = Options()
        #chrome_options.add_argument("--headless")
        caps = DesiredCapabilities().CHROME
        caps["pageLoadStrategy"] = "normal"  # Waits for full page load
        # caps["pageLoadStrategy"] = "none"
        # Selenium opening page
        driver = webdriver.Chrome(executable_path=const.WEBDRIVER_PATH,
                                  chrome_options=chrome_options,
                                  desired_capabilities=caps)
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

            self.df_oddschecker = self.df_oddschecker.append({
                'date': self.race_date_string,
                'time': time,
                'city': city,
                'horse': horse,
                'started': started,
                'oddschecker': odd_mean,
                'odd_list': odd_list
            }, ignore_index=True)

        driver.close()