import sys
sys.path.append('/home/alexandresalem/Projects/sportsbet')

from datetime import datetime, timedelta
from horse.bases import post_race_base
from horse.constants import RACING_HOURS
from horse.finance import new_daily_bets_result, new_monthly_results
from horse.mail import mail_results
from horse.scrapper import bbc

if __name__ == "__main__":
    date_us = datetime.now()
    date_uk = datetime.utcnow()
    tomorrow_uk = date_uk + timedelta(days=1)
    yesterday_uk = date_uk - timedelta(days=1)
    hour_us = date_us.hour
    hour_uk = date_uk.hour

    # mail_bets(date_uk.strftime("%Y.%m.%d"))

    if hour_uk >= RACING_HOURS[0]:
        bbc(date_uk.strftime('%Y.%m.%d'))
        post_race_base(date_uk.strftime('%Y.%m.%d'))
        new_daily_bets_result(date_uk.strftime("%Y.%m.%d"))
        new_monthly_results(date_uk.strftime("%Y.%m.%d"))

        mail_results(date_uk.strftime("%Y.%m.%d"))



    elif hour_uk < RACING_HOURS[0]:

        bbc(yesterday_uk.strftime('%Y.%m.%d'))
        post_race_base(yesterday_uk.strftime('%Y.%m.%d'))
        new_daily_bets_result(yesterday_uk.strftime("%Y.%m.%d"))
        new_monthly_results(yesterday_uk.strftime("%Y.%m.%d"))

        mail_results(yesterday_uk.strftime("%Y.%m.%d"))
