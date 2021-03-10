import os
from datetime import datetime, timedelta

import pandas as pd

from horse.constants import BASES_DIR, ODDSCHECKER_DIR, BETFAIR_DIR, ODDFAIR_DIR, HISTORICAL_BASES_DIR, DAILY_BASES_DIR, \
    BBC_DIR, CONSERVADOR, MEDIANO, AGRESSIVO

from horse.utils import financial_result, is_winner, prepare_bbc_dataset


def pre_race_base(date_string, refresh=False):

    file_extensions = ['_v1']
    if refresh:
        file_extensions.append('')

    for ext in file_extensions:
        oddschecker_filename = os.path.join(BASES_DIR, ODDSCHECKER_DIR, f'base_oddschecker_{date_string}{ext}.csv')
        df_oddschecker = pd.read_csv(oddschecker_filename, parse_dates=['date'])

        betfair_filename = os.path.join(BASES_DIR, BETFAIR_DIR, f'base_betfair_{date_string}{ext}.csv')
        df_betfair = pd.read_csv(betfair_filename, parse_dates=['date'])

        df_join = pd.merge(df_betfair,
                           df_oddschecker,
                           how='left',
                           on=['date', 'time', 'city', 'horse'],
                           suffixes=('_betfair', '_oddschecker'))

        df_join.sort_values(by=['time', 'oddschecker'], ignore_index=True, inplace=True)
        df_join.rename(columns={"oddschecker": "odds", "horses_race_betfair": "horses_race"},
                       errors="ignore",
                       inplace=True)

        historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
        df_history = pd.read_csv(historical_filename, low_memory=False, parse_dates=['date'])
        df_join = prepare_bbc_dataset(df_join, df_history, pre_race=True)


        # for index, column in df_join.iterrows():
        #
        #     if index:
        #         if column['city'] == df_join.loc[index-1, 'city'] and column['time'] == df_join.loc[index-1, 'time']:
        #             df_join.loc[index, 'started'] = df_join.loc[index - 1, 'started'] + 1
        #         else:
        #             df_join.loc[index, 'started'] = 1
        #
        # df_join = get_history(df_join)

        filename = os.path.join(BASES_DIR, ODDFAIR_DIR, f'base_pre_race_{date_string}{ext}.csv')
        df_join.to_csv(f'{filename}', index=False)

        print('Updating Pre Race Full')

        df_pre_race_full = pd.read_csv(os.path.join(BASES_DIR, 'base_pre_race_full.csv'))
        df_pre_race_full = df_pre_race_full.append(df_join)
        df_pre_race_full.drop_duplicates(subset=['date', 'time', 'city', 'horse'], keep='last', inplace=True)
        df_pre_race_full.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
        df_pre_race_full.to_csv(os.path.join(BASES_DIR, 'base_pre_race_full.csv'), index=False)


def get_history(df):
    df_bbc_full = pd.read_csv(os.path.join(BASES_DIR, 'base_bbc_full.csv'))
    df_bbc_full = df_bbc_full.drop_duplicates().sort_index(ascending=False, ignore_index=True)

    yesterday = (datetime.strptime(df.loc[0, "date"], '%Y.%m.%d') - timedelta(days=1)).strftime('%Y.%m.%d')
    df_history = pd.read_csv(os.path.join(BASES_DIR, HISTORICAL_BASES_DIR, f'base_historica_{yesterday}.csv'))

    for i in range(1, 6):
        df[f'race-{i}'] = ""
    df[f'adv1'] = ""
    for i in range(1, 6):
        df[f'adv1-{i}'] = ""
    df[f'adv2'] = ""
    for i in range(1, 6):
        df[f'adv2-{i}'] = ""

    df['jockey_won_last_15_days'] = 0
    df['jockey_won_yesterday'] = 0

    df['date'] = pd.to_datetime(df['date'])
    df_bbc_full['date'] = pd.to_datetime(df_bbc_full['date'])
    for index, row in df.iterrows():
        count = 0
        count2 = 0
        count3 = 0
        try:
            df_horse = df_bbc_full.loc[df_bbc_full['horse'] == row['horse']]
            df_horse['date'] = pd.to_datetime(df_horse['date'])
            for index2, row2 in df_horse.iterrows():

                if row2['date'] < row['date']:
                    count += 1
                    df.loc[index, f'race-{count}'] = row2['finished']

                    if count == 5:
                        break

            if row['started'] == 1:
                df.loc[index, f'adv1'] = df.loc[index + 1, 'horse']
                df.loc[index, f'adv1_odd'] = df.loc[index + 1, 'oddschecker']
                df.loc[index, f'adv2'] = df.loc[index + 2, 'horse']
                df.loc[index, f'adv2_odd'] = df.loc[index + 2, 'oddschecker']
                df_horse_adv1 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index + 1, 'horse']]
                df_horse_adv2 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index + 2, 'horse']]

            elif row['started'] == 2:
                df.loc[index, f'adv1'] = df.loc[index - 1, 'horse']
                df.loc[index, f'adv1_odd'] = df.loc[index - 1, 'oddschecker']
                df.loc[index, f'adv2'] = df.loc[index + 1, 'horse']
                df.loc[index, f'adv2_odd'] = df.loc[index + 1, 'oddschecker']
                df_horse_adv1 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index - 1, 'horse']]
                df_horse_adv2 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index + 1, 'horse']]

            else:
                df.loc[index, f'adv1'] = df.loc[index - row['started'] + 1, 'horse']
                df.loc[index, f'adv1_odd'] = df.loc[index - row['started'] + 1, 'oddschecker']
                df.loc[index, f'adv2'] = df.loc[index - row['started'] + 2, 'horse']
                df.loc[index, f'adv2_odd'] = df.loc[index - row['started'] + 2, 'oddschecker']
                df_horse_adv1 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index - row['started'] + 1, 'horse']]
                df_horse_adv2 = df_bbc_full.loc[df_bbc_full['horse'] == df.loc[index - row['started'] + 2, 'horse']]

            for index3, row3 in df_horse_adv1.iterrows():

                if row3['date'] < row['date']:
                    count2 += 1
                    df.loc[index, f'adv1-{count2}'] = row3['finished']

                    if count2 == 5:
                        break

            for index4, row4 in df_horse_adv2.iterrows():

                if row4['date'] < row['date']:
                    count3 += 1
                    df.loc[index, f'adv2-{count3}'] = row4['finished']

                    if count3 == 5:
                        break

        except Exception as e:
            print(e)
            pass

        try:

            df_jockey = df_history.loc[df_history['jockey'] == row['jockey']]
            df_jockey['date'] = pd.to_datetime(df_jockey['date'])
            df_jockey = df_jockey[df_jockey['date'] < row['date']]
            df_jockey = df_jockey[df_jockey['date'] >= row['date'] - timedelta(days=15)]

            for index2, row2 in df_jockey.iterrows():
                if row2['finished'] == '1':
                    df.loc[index, f'jockey_won_last_15_days'] = 1
                    break

            for index2, row2 in df_jockey.iterrows():
                if row2['date'] == row['date'] - timedelta(days=1):
                    if row2['finished'] == '1':
                        df.loc[index, f'jockey_won_yesterday'] = row2['finished']
                        break

        except Exception as e:
            print(e)

    df.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
    for i in range(1, 6):
        df[f'race-{i}'] = pd.to_numeric(df[f'race-{i}'], errors='coerce')
        df[f'adv1-{i}'] = pd.to_numeric(df[f'adv1-{i}'], errors='coerce')
        df[f'adv2-{i}'] = pd.to_numeric(df[f'adv2-{i}'], errors='coerce')

    df['best_position'] = df[['race-1', 'race-2', 'race-3', 'race-4', 'race-5']].min(axis=1)
    df['best_position_adv1'] = df[['adv1-1', 'adv1-2', 'adv1-3', 'adv1-4', 'adv1-5']].min(axis=1)
    df['best_position_adv2'] = df[['adv2-1', 'adv2-2', 'adv2-3', 'adv2-4', 'adv2-5']].min(axis=1)

    df['won_last_race'] = df.apply(lambda x: is_winner(x['race-1']), axis=1)
    df['won_last_race_adv1'] = df.apply(lambda x: is_winner(x['adv1-1']), axis=1)
    df['won_last_race_adv2'] = df.apply(lambda x: is_winner(x['adv2-1']), axis=1)

    return df


def post_race_base(date_string):
    print('Atualizando base pós corridas')

    pre_race_filename = os.path.join(BASES_DIR, ODDFAIR_DIR, f'base_pre_race_{date_string}.csv')
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
            bbc_filename = os.path.join(BASES_DIR, BBC_DIR, f'base_bbc_{date_string}.csv')
            df_bbc = pd.read_csv(bbc_filename)
            df_bbc = df_bbc[['date', 'time', 'city', 'horse', 'finished', 'horse_age', 'horse_weight', 'trainer', 'gap']]
            df_join = pd.merge(df_day, df_bbc, how='left', on=['date', 'time', 'city', 'horse'])

        df_join['result_conservador'] = df_join.apply(
            lambda row: financial_result(CONSERVADOR, row['betfair_back'], row['finished']), axis=1)
        df_join['result_mediano'] = df_join.apply(
            lambda row: financial_result(MEDIANO, row['betfair_back'], row['finished']), axis=1)
        df_join['result_agressivo'] = df_join.apply(
            lambda row: financial_result(AGRESSIVO, row['betfair_back'], row['finished']), axis=1)

        # Winner
        df_join['winner'] = df_join.apply(lambda x: is_winner(x['finished']), axis=1)

        post_race_filename = os.path.join(BASES_DIR, DAILY_BASES_DIR, f'base_horse_finished_{date_string}.csv')
        df_join.to_csv(post_race_filename, index=False)

        historical_base(date_string)


def historical_base(date_string):
    yesterday = (datetime.strptime(date_string, '%Y.%m.%d') - timedelta(days=1)).strftime('%Y.%m.%d')

    problem = True
    while problem:
        try:
            historical_filename = os.path.join(BASES_DIR, HISTORICAL_BASES_DIR, f'base_historica_{yesterday}.csv')
            df_all = pd.read_csv(historical_filename)
            problem = False
        except:
            yesterday = (datetime.strptime(yesterday, '%Y.%m.%d') - timedelta(days=1)).strftime('%Y.%m.%d')

    daily_filename = os.path.join(BASES_DIR, DAILY_BASES_DIR, f'base_horse_finished_{date_string}.csv')
    df_day = pd.read_csv(daily_filename)
    df_day['date'] = pd.to_datetime(df_day['date']).dt.strftime('%Y-%m-%d')

    df_all = df_all.append(df_day, ignore_index=True)
    filename = os.path.join(BASES_DIR, HISTORICAL_BASES_DIR, f'base_historica_{date_string}.csv')
    df_all = df_all.dropna(subset=['finished', 'started'])
    df_all.to_csv(filename, index=False)
