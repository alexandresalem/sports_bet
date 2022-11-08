from datetime import datetime

from horse.bases import merging_bases
from horse.bet import Bet
from horse.mail import mail_bets
from horse.models import run_new_model
from horse.scheduler import schedule_tasks
from horse.utils import logger

if __name__ == "__main__":
    try:
        bets = Bet()
        bets.scrap()
        merging_bases(bets.date_uk.strftime('%Y.%m.%d'), bets.racing_hours)
        run_new_model(bets.date_uk.strftime("%Y.%m.%d"),
                      racing_hours=bets.racing_hours)
        if not bets.racing_hours:
            schedule_tasks(bets.race_times, bets.date_uk)
        else:
            mail_bets(bets.date_uk.strftime("%Y.%m.%d"), bets.racing_hours)
        bets.send_telegram_predictions()
    except Exception as e:
        logger.info(e)
