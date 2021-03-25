import logging
import sys
sys.path.append('/home/alexandresalem/Projects/sportsbet')

from datetime import datetime, timedelta
from horse.bases import post_race_base, pre_race_base
from horse.constants import RACING_HOURS
from horse.finance import new_daily_bets_result, new_monthly_results
from horse.mail import mail_bets
from horse.models import run_new_model
from horse.scrapper import oddschecker, betfair, bbc

if __name__ == "__main__":
    date_us = datetime.now()
    date_uk = datetime.utcnow()
    tomorrow_uk = date_uk + timedelta(days=1)
    yesterday_uk = date_uk - timedelta(days=1)
    hour_us = date_us.hour
    hour_uk = date_uk.hour
    if hour_uk in RACING_HOURS:
        # Durante o expediente, atualiza somente o resultado dos palpites
        driver, races = oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False, racing_hours=True)

        if races:
            betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=False, racing_hours=True, driver=driver)
            driver.close()
            driver.quit()

            pre_race_base(date_uk.strftime('%Y.%m.%d'), racing_hours=True)
            run_new_model(date_uk.strftime("%Y.%m.%d"), racing_hours=True)
            # mail_bets(date_uk.strftime("%Y.%m.%d"))
        else:
            driver.close()
            driver.quit()

    elif hour_uk >= RACING_HOURS[-1]:
        # # Após as corridas, mas ainda no mesmo dia que os EUA
        driver, races = oddschecker(tomorrow_uk.strftime('%Y.%m.%d'), next_day_screen=True)
        betfair(tomorrow_uk.strftime('%Y.%m.%d'), next_day_screen=True, driver=driver)
        if driver:
            driver.close()
            driver.quit()

        pre_race_base(tomorrow_uk.strftime('%Y.%m.%d'))
        run_new_model(tomorrow_uk.strftime("%Y.%m.%d"))

    elif hour_uk < RACING_HOURS[0]:

        if hour_us >= (24 + date_uk.hour - date_us.hour):
            driver, races = oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False)
            betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=True, driver=driver)
        else:
            driver, races = oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False)
            betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=False, driver=driver)

        if driver:
            driver.close()
            driver.quit()

        pre_race_base(date_uk.strftime('%Y.%m.%d'))
        run_new_model(date_uk.strftime("%Y.%m.%d"))
