from horse.scrapper import Oddschecker
import horse.constants as const
from horse.scheduler import Telegram
import os
import pandas as pd


class Bet(Oddschecker, Telegram):
    def __init__(self):
        Oddschecker.__init__(self)
        Telegram.__init__(self)
