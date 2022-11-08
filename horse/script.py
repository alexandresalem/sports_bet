from cmath import exp
from datetime import datetime, timedelta

import pandas as pd

from horse.bases import merging_bases, post_race_base, pre_race_base
from horse.constants import RACING_HOURS
from horse.finance import new_daily_bets_result, new_monthly_results
from horse.mail import mail_bets
from horse.models import build_new_model, run_new_model
from horse.scrapper import bbc

if __name__ == "__main__":
    build_new_model()
    initial_date = datetime(2022, 11, 7)
    for i in range(1):
        date_string = (initial_date + timedelta(i)).strftime('%Y.%m.%d')
    #     try:
    #         print(datetime.now(), 'Comecando')
    #         merging_bases(date_string)
     #   run_new_model(date_string)
        # bbc(date_string)
        new_daily_bets_result(date_string)
        # new_monthly_results(date_string)

    # #         print(datetime.now(), 'Final')
    # #     except Exception as e:
    # #         print(e)
    # #         pass
    #     send_telegram_message(date_string=date_string)
