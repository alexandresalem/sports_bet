from horse.bet import Bet
from horse.mail import mail_bets
from horse.scheduler import send_telegram_message
from horse.models import run_new_model
from horse.bases import merging_bases
from datetime import datetime
from horse.utils import logger


if __name__ == "__main__":
    try:
        bets = Bet()
        bets.scrap(race_day=True)
        merging_bases(bets.date_uk.strftime('%Y.%m.%d'), racing_hours=True)
        run_new_model(bets.date_uk.strftime("%Y.%m.%d"), racing_hours=True)
        mail_bets(bets.date_uk.strftime("%Y.%m.%d"), racing_hours=True)
        send_telegram_message(bets.date_uk.strftime(
            '%Y.%m.%d'), racing_hours=True)
    except Exception as e:
        logger.info(e)
