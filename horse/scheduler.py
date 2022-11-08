from datetime import datetime, timedelta
import pandas as pd
import pytz
import os
import win32com.client
from telegram.ext import *
import telegram.parsemode


import horse.constants as const
from horse.utils import logger


def schedule_tasks(races, race_date):
    task = win32com.client.Dispatch('Schedule.Service')
    task.Connect()

    root_folder = task.GetFolder('\\')
    newtask = task.NewTask(0)

    logger.info(f'Scheduling {len(races)} tasks in Windows')
    # Trigger
    for race in races:
        race_time = datetime.strptime(race, '%H:%M')
        race_time = race_time.replace(year=race_date.year,
                                      month=race_date.month,
                                      day=race_date.day,
                                      tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/London"))
        set_time = race_time - timedelta(minutes=const.MINUTES_INTERVAL)
        TASK_TRIGGER_TIME = 1
        trigger = newtask.Triggers.Create(TASK_TRIGGER_TIME)
        trigger.StartBoundary = set_time.isoformat()

    # Action
    TASK_ACTION_EXEC = 0
    action = newtask.Actions.Create(TASK_ACTION_EXEC)
    action.ID = 'DO NOTHING'
    action.Path = r'C:\Users\Alexandre\Projects\venv\bet\Scripts\python.exe'
    action.Arguments = r'C:\Users\Alexandre\Projects\sports_bet\horse\main.py'

    # Parameters
    newtask.RegistrationInfo.Description = 'Python Task Test'
    newtask.Settings.Enabled = True
    newtask.Settings.StopIfGoingOnBatteries = False

    # Saving
    TASK_CREATE_OR_UPDATE = 6
    TASK_LOGON_NONE = 1
    root_folder.RegisterTaskDefinition(
        'Oddschecker_Intraday',  # Python Task Test
        newtask,
        TASK_CREATE_OR_UPDATE,
        'Alexandre',  # No user
        'abuabu444',  # No password
        TASK_LOGON_NONE)

    logger.info(f'Tasks scheduled sucessfully')


class Telegram():
    def __init__(self):
        self.telegram_updater = Updater(
            const.TELEGRAM_API_KEY, use_context=True)

    def send_telegram_message(self, text):
        with open(r'C:\Users\Alexandre\telegram.txt', 'r') as file:
            key = file.read()
        self.telegram_updater.bot.sendMessage(
            chat_id=key, text=text, parse_mode=telegram.parsemode.ParseMode.MARKDOWN)

    def send_telegram_predictions(self):
        ext = '_v0' if self.racing_hours else '_v1'
        date_string = self.date_uk.strftime("%Y.%m.%d")
        logger.info(f'Sending Telegram Message')

        models = os.path.join(const.MODELOS_DIR, 'models.csv')
        df_models = pd.read_csv(models)

        for index, column in df_models.iterrows():

            if not pd.isnull(column["use"]):
                bets_filename = os.path.join(
                    const.BASES_DIR, const.BETS_DIR, f'aposta_{column["name"]}_{date_string}{ext}.csv')

                df = pd.read_csv(bets_filename, parse_dates=['time'])
                num_races = df['time'].nunique()
                first_race_time = df['time'].min()
                first_race_time_br = first_race_time.replace(
                    tzinfo=pytz.timezone("Europe/London")).astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M")

                count = len(df)
                time_uk = datetime.utcnow().replace(
                    tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/London"))
                time_uk = time_uk.replace(tzinfo=None)
                df.reset_index(drop=True, inplace=True)
                if self.racing_hours:
                    df = df[df['time'] > time_uk]
                    logger.info(len(df))
                    df.sort_values(by=['date', 'city', 'time',
                                       'loose_chance'], inplace=True)
                    if len(df) == len(df[df['winner_pred'] != 1]):
                        for index, row in df.iterrows():
                            city = row['city'].capitalize()
                            time_br = row['time'].replace(
                                tzinfo=pytz.timezone("Europe/London")).astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M")
                            text = f"*{city}: {time_br} (BR) - {row['time'].strftime('%H:%M')} (UK)* \nAlgoritmo não sugeriu apostas para esta corrida."
                            self.send_telegram_message(text=text)
                            break

                    else:
                        df = df[df['winner_pred'] == 1]
                        for index, row in df.iterrows():
                            horse = row['horse'].capitalize()
                            city = row['city'].capitalize()
                            time_br = row['time'].replace(
                                tzinfo=pytz.timezone("Europe/London")).astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%H:%M")
                            text = f"*{city}: {time_br} (BR) - {row['time'].strftime('%H:%M')} (UK)* \nAposta sugerida: *{horse}*"
                            self.send_telegram_message(text=text)
                else:
                    text = f"Algortimo preparado para processar as corridas de amanha ({date_string}). \nSerao {num_races} corridas e a primeira ira comecar as *{first_race_time_br} (BR) - {first_race_time.strftime('%H:%M')} (UK)*"
                    self.send_telegram_message(text=text)
