from datetime import datetime, timedelta
from horse.scrapper import bbc
from pytz import timezone

initial_date = datetime(2019, 3, 16)

for i in range(0, 1000):
    date = initial_date + timedelta(days=i)
    try:
        bbc(date.strftime('%Y.%m.%d'))
    except:
        x = 1