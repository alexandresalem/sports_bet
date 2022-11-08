import gc
import os
from datetime import datetime, timedelta

import pandas as pd

from horse.constants import BASES_DIR, ODDSCHECKER_DIR, BETFAIR_DIR, ODDFAIR_DIR, HISTORICAL_BASES_DIR, DAILY_BASES_DIR, \
    BBC_DIR, CONSERVADOR, MEDIANO, AGRESSIVO, MINUTES_INTERVAL

from horse.utils import financial_result, is_winner, prepare_bbc_dataset, logger


def merging_bases(date_string, racing_hours=False):
    ext = '_v0' if racing_hours else '_v1'
    oddschecker_filename = os.path.join(
        BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}{ext}.csv')
    df_oddschecker = pd.read_csv(
        oddschecker_filename, parse_dates=['date', 'time'])

    df_oddschecker['time'] = df_oddschecker['time'].dt.strftime("%H:%M")
    df_oddschecker.rename(columns={"oddschecker": "odds"},
                          errors="ignore",
                          inplace=True)
    df_oddschecker.sort_values(
        by=['time', 'odds'], ignore_index=True, inplace=True)

    historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
    df_history = pd.read_csv(
        historical_filename, low_memory=False, parse_dates=['date'])

    df_oddschecker = prepare_bbc_dataset(
        df_oddschecker, df_history, pre_race=True)
    filename = os.path.join(BASES_DIR, ODDFAIR_DIR,
                            f'base_pre_race_{date_string}{ext}.csv')
    df_oddschecker.to_csv(f'{filename}', index=False)
    del df_history
    gc.collect()


def pre_race_base(date_string, racing_hours=False):

    ext = '' if racing_hours else '_v1'

    oddschecker_filename = os.path.join(
        BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}{ext}.csv')
    betfair_filename = os.path.join(
        BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')

    try:
        df_oddschecker = pd.read_csv(
            oddschecker_filename, parse_dates=['date', 'time'])
        df_betfair = pd.read_csv(
            betfair_filename, parse_dates=['date', 'time'])

        df_join = pd.merge(df_betfair,
                           df_oddschecker,
                           how='left',
                           on=['date', 'time', 'city', 'horse'],
                           suffixes=('_betfair', '_oddschecker'))

        if df_join['oddschecker'].isnull().sum() == len(df_join):
            df_betfair['time'] = df_betfair['time'] + pd.Timedelta(hours=1)
            df_join = pd.merge(df_betfair,
                               df_oddschecker,
                               how='left',
                               on=['date', 'time', 'city', 'horse'],
                               suffixes=('_betfair', '_oddschecker'))

        df_join['time'] = df_join['time'].dt.strftime("%H:%M")

        df_join.rename(columns={"oddschecker": "odds", "horses_race_betfair": "horses_race"},
                       errors="ignore",
                       inplace=True)

        df_join.sort_values(by=['time', 'odds'],
                            ignore_index=True, inplace=True)

        historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
        df_history = pd.read_csv(
            historical_filename, low_memory=False, parse_dates=['date'])

        df_join = prepare_bbc_dataset(df_join, df_history, pre_race=True)
        filename = os.path.join(BASES_DIR, ODDFAIR_DIR,
                                f'base_pre_race_{date_string}{ext}.csv')
        df_join.to_csv(f'{filename}', index=False)
        del df_history
        gc.collect()

    except FileNotFoundError:
        logger.error(
            f'Pre-race: Ainda não tiveram corridas iniciadas no dia {date_string}')

    # print('Updating Pre Race Full')
    # df_pre_race_full = pd.read_csv(os.path.join(BASES_DIR, 'base_pre_race_full.csv'))
    # df_pre_race_full = df_pre_race_full.append(df_join)
    # df_pre_race_full.drop_duplicates(subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
    # df_pre_race_full.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
    # df_pre_race_full.to_csv(os.path.join(BASES_DIR, 'base_pre_race_full.csv'), index=False)


def post_race_base(date_string):
    print('Atualizando base pós corridas')

    pre_race_filename = os.path.join(
        BASES_DIR, ODDFAIR_DIR, f'base_pre_race_{date_string}.csv')
    skip = False
    try:
        df_day = pd.read_csv(pre_race_filename)
        df_day['date'] = df_day['date'].str.replace("-", ".")
    except:
        skip = True

    if not skip:
        df_day = df_day[df_day['date'] == date_string]

        if 'gap' in df_day:
            df_join = df_day
        else:
            bbc_filename = os.path.join(
                BASES_DIR, BBC_DIR, f'base_bbc_{date_string}.csv')
            df_bbc = pd.read_csv(bbc_filename)
            df_bbc = df_bbc[['date', 'time', 'city', 'horse',
                             'finished', 'horse_age', 'horse_weight', 'trainer', 'gap']]
            df_join = pd.merge(df_day, df_bbc, how='left', on=[
                               'date', 'time', 'city', 'horse'])

        df_join['result_conservador'] = df_join.apply(
            lambda row: financial_result(CONSERVADOR, row['betfair_back'], row['finished']), axis=1)
        df_join['result_mediano'] = df_join.apply(
            lambda row: financial_result(MEDIANO, row['betfair_back'], row['finished']), axis=1)
        df_join['result_agressivo'] = df_join.apply(
            lambda row: financial_result(AGRESSIVO, row['betfair_back'], row['finished']), axis=1)

        # Winner
        df_join['winner'] = df_join.apply(
            lambda x: is_winner(x['finished']), axis=1)

        post_race_filename = os.path.join(
            BASES_DIR, DAILY_BASES_DIR, f'base_horse_finished_{date_string}.csv')
        df_join.to_csv(post_race_filename, index=False)

        historical_base(date_string)


def historical_base(date_string):
    yesterday = (datetime.strptime(date_string, '%Y.%m.%d') -
                 timedelta(days=1)).strftime('%Y.%m.%d')

    problem = True
    while problem:
        try:
            historical_filename = os.path.join(
                BASES_DIR, HISTORICAL_BASES_DIR, f'base_historica_{yesterday}.csv')
            df_all = pd.read_csv(historical_filename)
            problem = False
        except:
            yesterday = (datetime.strptime(yesterday, '%Y.%m.%d') -
                         timedelta(days=1)).strftime('%Y.%m.%d')

    daily_filename = os.path.join(
        BASES_DIR, DAILY_BASES_DIR, f'base_horse_finished_{date_string}.csv')
    df_day = pd.read_csv(daily_filename)
    df_day['date'] = pd.to_datetime(df_day['date']).dt.strftime('%Y-%m-%d')

    df_all = df_all.append(df_day, ignore_index=True)
    filename = os.path.join(BASES_DIR, HISTORICAL_BASES_DIR,
                            f'base_historica_{date_string}.csv')
    df_all = df_all.dropna(subset=['finished', 'started'])
    df_all.to_csv(filename, index=False)
