#!/usr/bin/python3

from datetime import datetime, timedelta

from horse.bases import post_race_base, pre_race_base
from horse.finance import new_daily_bets_result, new_monthly_results
from horse.models import run_new_model
from horse.scrapper import oddschecker, betfair, bbc

if __name__ == "__main__":
    date_us = datetime.now()
    date_uk = datetime.utcnow()
    tomorrow_uk = date_uk + timedelta(days=1)
    yesterday_uk = date_uk - timedelta(days=1)
    hour_us = date_us.hour
    hour_uk = date_uk.hour

    if hour_uk in range(11, 21):
        # Durante o expediente, atualiza somente o resultado dos palpites
        oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False, refresh=True)
        betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=False, refresh=True)
        pre_race_base(date_uk.strftime('%Y.%m.%d'), refresh=True)
        run_new_model(date_uk.strftime("%Y.%m.%d"), refresh=True)

        bbc(date_uk.strftime('%Y.%m.%d'))
        new_daily_bets_result(date_uk.strftime("%Y.%m.%d"))
        new_monthly_results(date_uk.strftime("%Y.%m.%d"))

    elif hour_uk >= 21:
        # bbc(date_uk.strftime('%Y.%m.%d'))
        new_daily_bets_result(date_uk.strftime("%Y.%m.%d"))
        new_monthly_results(date_uk.strftime("%Y.%m.%d"))

        # # Após as corridas, mas ainda no mesmo dia que os EUA
        # oddschecker(tomorrow_uk.strftime('%Y.%m.%d'), next_day_screen=True)
        # betfair(tomorrow_uk.strftime('%Y.%m.%d'), next_day_screen=True)
        # pre_race_base(tomorrow_uk.strftime('%Y.%m.%d'))
        # run_new_model(tomorrow_uk.strftime("%Y.%m.%d"))

    elif hour_uk < 11:

        bbc(yesterday_uk.strftime('%Y.%m.%d'))
        post_race_base(yesterday_uk.strftime('%Y.%m.%d'))
        new_daily_bets_result(yesterday_uk.strftime("%Y.%m.%d"))
        new_monthly_results(yesterday_uk.strftime("%Y.%m.%d"))

        if hour_us >= 18:
            oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False)
            betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=True)
        else:
            oddschecker(date_uk.strftime('%Y.%m.%d'), next_day_screen=False)
            betfair(date_uk.strftime('%Y.%m.%d'), next_day_screen=False)

        pre_race_base(date_uk.strftime('%Y.%m.%d'))
        run_new_model(date_uk.strftime("%Y.%m.%d"))
