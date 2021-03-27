import os
import pandas as pd
from datetime import datetime

from jinja2 import Template, Environment, FileSystemLoader
from horse.constants import MODELOS_DIR, BASES_DIR, BETS_DIR, BETS_RESULT_DIR, FINANCEIRO_DIR
from horse.utils import send_mail, logger


def mail_bets(date_string):
    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)

    for index, column in df_models.iterrows():

        if not pd.isnull(column["use"]):
            bets_filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}.csv')

            try:
                df = pd.read_csv(bets_filename, parse_dates=['time'])
                df = df[df['winner_pred'] == 1]
                df.sort_values(by=['date', 'city', 'time', 'loose_chance'], inplace=True)
                count = len(df['winner_pred'] == 1)

                utc_now = datetime.utcnow()
                bets_df = df[df['time'] > utc_now]
                bets_df.reset_index(drop=True, inplace=True)

                if len(bets_df):
                    env = Environment(loader=FileSystemLoader("/home/alexandresalem/Projects/sportsbet/horse/templates"))
                    tm = env.get_template("mail_bets.html")
                    msg = tm.render(results=bets_df)
                    logger.warning('Enviando email apostas')
                    send_mail(msg, subject=f"{count}ª aposta do dia")

            except Exception as e:

                print(e)


def mail_results(date_string):
    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)

    for index, column in df_models.iterrows():

        if not pd.isnull(column["use"]):
            results_filename = os.path.join(BASES_DIR,
                                            BETS_RESULT_DIR,
                                            f'resultados_{column["name"]}_{date_string}_v1.csv')

            finance_filename = os.path.join(BASES_DIR,
                                            FINANCEIRO_DIR,
                                            f'financeiro_{column["name"]}_{date_string}_v1.csv')


            try:

                df = pd.read_csv(results_filename)
                df.sort_values(by=['date', 'time', 'city'], inplace=True, ignore_index=True)

                df_fin = pd.read_csv(finance_filename)
                df_fin.rename(columns={"Unnamed: 0": "date"}, errors="ignore", inplace=True)

                df_fin = df_fin.iloc[2:, :]
                df_fin.reset_index(drop=True, inplace=True)
                df_fin['conservador'] = df_fin['conservador'].astype('float32')

                if len(df):
                    result = df_fin.loc[0, 'conservador']

                    if result > 0:
                        title = "Lucro"
                    else:
                        title = "Prejuizo"
                        round()
                    if datetime.utcnow().hour < 21:
                        subject = f"Parcial Apostas {date_string}: {title} de {round(result, 2)}%"
                    else:
                        subject = f"Resultado Final {date_string}: {title} de {round(result, 2)}%"

                    env = Environment(loader=FileSystemLoader("/home/alexandresalem/Projects/sportsbet/horse/templates"))
                    tm = env.get_template("mail_results.html")
                    msg = tm.render(results=df, finance=df_fin)
                    logger.warning('Enviando email resultados')
                    send_mail(msg, subject=subject)

            except Exception as e:

                print(e)
