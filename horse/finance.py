import os
from datetime import datetime, timedelta

import pandas as pd

from horse.constants import MODELOS_DIR, BASES_DIR, BBC_DIR, BETS_DIR, \
    BETS_RESULT_DIR, CONSERVADOR, MEDIANO, AGRESSIVO, FINANCEIRO_DIR
from horse.scrapper import bbc
from horse.utils import financial_result, strategy, new_strategy, is_winner


def new_daily_bets_result(date_string, days=1):

    df_models = pd.read_csv(os.path.join(MODELOS_DIR, 'models.csv'))
    for index, column in df_models.iterrows():

        if not pd.isnull(column['use']):
            bbc_filename = os.path.join(BASES_DIR, BBC_DIR, f'base_bbc_{date_string}.csv')

            extensions_list = ['', '_v1']
            for ext in extensions_list:
                if days > 1:

                    bets_filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}_days_{days}{ext}.csv')

                    files = os.listdir(os.path.join(BASES_DIR, BBC_DIR))

                    date_list = [(datetime.strptime(date_string, '%Y.%m.%d') - timedelta(days=x)).strftime('%Y.%m.%d')
                                 for x in range(days)]

                    files_list = []

                    for day in date_list:
                        if f'base_bbc_{day}.csv' in files:
                            files_list.append(os.path.join(BASES_DIR,
                                                           BBC_DIR,
                                                           f'base_bbc_{day}.csv'))
                    output_filename = os.path.join(BASES_DIR,
                                                   BETS_RESULT_DIR,
                                                   f'resultados_{column["name"]}_{date_string}_days_{days}{ext}.csv')
                else:
                    bets_filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}{ext}.csv')
                    output_filename = os.path.join(BASES_DIR,
                                                   BETS_RESULT_DIR,
                                                   f'resultados_{column["name"]}_{date_string}{ext}.csv')



                # if f'resultados_{column["name"]}_{date_string}.csv' in os.listdir(os.path.join(BASES_DIR, BETS_RESULT_DIR)):
                #     os.remove(output_filename)


                try:

                    if days > 1:
                        df_bbc = pd.concat([pd.read_csv(file, parse_dates=['date']) for file in files_list],
                                               axis=0,
                                               join='inner').sort_values(by=['date', 'city', 'time'])
                    else:
                        df_bbc = pd.read_csv(bbc_filename, parse_dates=['date'])

                    df_bbc.rename(columns={"oddschecker": "odds"}, errors="ignore", inplace=True)

                    df_bets = pd.read_csv(bets_filename, parse_dates=['date'])
                    df_bets = new_strategy(df_bets)

                    if len(df_bets):
                        df_finance = pd.merge(df_bets,
                                              df_bbc,
                                              how='left',
                                              on=['date', 'time', 'city', 'horse']
                                              )

                        df_finance['finished'] = df_finance['finished'].astype('str').replace('nan', 'Não Finalizada')

                        df_finance = df_finance[df_finance['finished'] != 'NR']
                        df_finance = df_finance[df_finance['finished'] != 'Não Finalizada']

                        if len(df_finance):
                            df_finance = df_finance.sort_values(by='time', ignore_index=True)

                            df_finance['num_apostas'] = 1

                            df_finance['acc_apostas'] = df_finance.apply(lambda row: is_winner(row['finished']), axis=1)

                            df_finance['conservador'] = df_finance.apply(
                                lambda row: financial_result(CONSERVADOR, row['betfair_back'], row['finished']),
                                axis=1)
                            # df_finance['mediano'] = df_finance.apply(
                            #     lambda row: financial_result(MEDIANO, row['betfair_back'], row['finished']), axis=1)
                            # df_finance['agressivo'] = df_finance.apply(
                            #     lambda row: financial_result(AGRESSIVO, row['betfair_back'], row['finished']),
                            #     axis=1)

                            df_finance['conservador_timeline'] = df_finance['conservador'].cumsum()
                            # df_finance['mediano_timeline'] = df_finance['mediano'].cumsum()
                            # df_finance['agressivo_timeline'] = df_finance['agressivo'].cumsum()

                            count = 1
                            for index2, column2 in df_finance.iterrows():
                                if column2['conservador_timeline'] > 8:
                                    df_finance.loc[index2, 'estrategia'] = column2['conservador_timeline']
                                    break

                                # if column['conservador_timeline'] <= -10:
                                #     df_finance.loc[index, 'estrategia'] = column['conservador_timeline']
                                #     break

                                if len(df_finance) == count:
                                    df_finance.loc[index2, 'estrategia'] = column2['conservador_timeline']
                                count += 1

                            df_finance.to_csv(output_filename, index=False)
                        else:
                            print(f'Não houve apostas para este criterio em {date_string}')

                except Exception as e:
                    print(f'Arquivo {bbc_filename} não encontrado. Verifique se houve corrida no dia.')
                    print(e)
                    pass


def new_monthly_results(date_string):
    date_list = [(datetime.strptime(date_string, '%Y.%m.%d') - timedelta(days=x)).strftime('%Y.%m.%d')
                 for x in range(90)]

    df_models = pd.read_csv(os.path.join(MODELOS_DIR, 'models.csv'))
    for index, column in df_models.iterrows():

        if not pd.isnull(column['use']):
            df = None



            extensions_list = ['', '_v1']
            for ext in extensions_list:
                table = False
                for day in date_list[len(date_list)::-1]:
                    file = os.path.join(BASES_DIR,
                                        BETS_RESULT_DIR,
                                        f'resultados_{column["name"]}_{day}{ext}.csv')


                    try:
                        if table:
                            df = df.append(pd.read_csv(file), ignore_index=True)
                        else:
                            df = pd.read_csv(file)
                            table = True
                    except:
                        continue

                try:
                    df = df.groupby(by=['date']).agg({'num_apostas': 'sum',
                                                      'acc_apostas': 'sum',
                                                      'conservador': 'sum',
                                                      # 'mediano': 'sum',
                                                      # 'agressivo': 'sum',
                                                      'estrategia': 'sum',
                                                      'conservador_timeline': ['min', 'max']})

                    df.sort_values(by=['date'], ascending=False, inplace=True)
                    df['retorno_estrategia_dia'] = (100 + df['estrategia']) / 100
                    df['retorno_dia_conservador'] = (100 + df['conservador']) / 100
                    # df['retorno_dia_mediano'] = (100 + df['mediano']) / 100
                    # df['retorno_dia_agressivo'] = (100 + df['agressivo']) / 100

                    df['retorno_max_dia_conservador'] = (100 + df['conservador_timeline']['max']) / 100
                    # df['retorno_max_dia_mediano'] = (100 + df['mediano_timeline']['max']) / 100
                    # df['retorno_max_dia_agressivo'] = (100 + df['agressivo_timeline']['max']) / 100

                    df['retorno_min_dia_conservador'] = (100 + df['conservador_timeline']['min']) / 100
                    # df['retorno_min_dia_mediano'] = (100 + df['mediano_timeline']['min']) / 100
                    # df['retorno_min_dia_agressivo'] = (100 + df['agressivo_timeline']['min']) / 100

                    df['retorno_estrategia_mes'] = df['retorno_estrategia_dia'].cumprod() * 100
                    df['retorno_mes_conservador'] = df['retorno_dia_conservador'].cumprod() * 100
                    # df['retorno_mes_mediano'] = df['retorno_dia_mediano'].cumprod() * 100
                    # df['retorno_mes_agressivo'] = df['retorno_dia_agressivo'].cumprod() * 100

                    df['retorno_max_conservador'] = df['retorno_max_dia_conservador'].cumprod() * 100
                    # df['retorno_max_mediano'] = df['retorno_max_dia_mediano'].cumprod() * 100
                    # df['retorno_max_agressivo'] = df['retorno_max_dia_agressivo'].cumprod() * 100

                    df = round(df, 4)

                    filename = os.path.join(BASES_DIR,
                                            FINANCEIRO_DIR,
                                            f'financeiro_{column["name"]}_{date_string}{ext}.csv')

                    df.to_csv(filename, index=True)
                except Exception as e:
                    print(e)
