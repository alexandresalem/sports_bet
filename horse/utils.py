import logging
import os
import smtplib
from datetime import timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from sklearn.preprocessing import LabelEncoder

from horse.constants import BASES_DIR, FINANCE_MAIL_LIST, CONSERVADOR

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename='horse_race.log',
                    filemode='a+')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)

# Now, define a couple of other loggers which might represent areas in your
# application:
logger = logging.getLogger()




def race_category(title, category):
    if category in title.lower():
        return 1
    return 0


def send_mail(template,
              attached_files=[],
              mail_to=FINANCE_MAIL_LIST,
              subject='Horse Race',
              ):

    with open('/home/alexandresalem/mail_info', 'r') as file:
        text = file.read()
    gmail_user = text.split(':')[0]
    gmail_password = text.split(':')[1].replace('\n', '')
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = gmail_user
    message['To'] = ""
    message['Cco'] = ",".join(mail_to)

    message.attach(MIMEText(template, "html"))

    part = MIMEBase('application', "octet-stream")

    #    I have a CSV file named `attachthisfile.csv` in the same directory that I'd like to attach an
    for file in attached_files:
        part.set_payload(open(f"{file}", "rb").read())
        encoders.encode_base64(part)
        filename = os.path.basename(file)
        part.add_header('Content-Disposition', 'attachment', filename=f'{filename}')
        message.attach(part)

    msgBody = message.as_string()

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)
    server.sendmail(gmail_user, mail_to, msgBody)
    server.quit()


def financial_result(bet, back, finished, started=1):

    try:
        if int(finished) == 1:
            return round(bet/started * (back - 1), 2)
        else:
            return round((-1) * bet/started, 2)
    except:
        if finished in ['NR', 'Não Finalizada']:
            return round(0, 2)
        else:
            return round((-1) * bet/started, 2)


def financial_result_model(bet, back, winner, winner_pred):

    try:
        if winner_pred == 1:
            if winner == 1:
                return round(bet * (back - 1), 2)
            else:
                return round((-1) * bet, 2)
        else:
            return 0
    except:
        return 0


def finishing_position(position, num_horses):
    try:
        return int(position)
    except:
        try:
            return int(num_horses)
        except:
            return 99


def is_winner(finished):
    try:
        if int(finished) == 1:
            return 1
        else:
            return 0
    except:
        return 0


def distance_bbc(distance):
    miles_list = distance.split('m')
    miles = int(miles_list[0].strip())
    furlongs_list = miles_list[1].split('f')
    furlongs = int(furlongs_list[0].strip())
    yards_list = furlongs_list[1].split('y')
    yards = int(yards_list[0].strip())

    return (miles * 1760) + (furlongs * 220)


def distance_in_yards(distance):
    try:
        miles_list = distance.split(r'*m')
        if len(miles_list) > 1:
            miles = int(miles_list[0].strip())
            furlong_list = miles_list[1].split(r'*f')
        else:
            miles = 0
            furlong_list = distance.split(r'*f')

        if len(furlong_list) > 1:
            furlongs = int(furlong_list[0].strip())
            yards_list = furlong_list[1].split(r'*y')
        else:
            furlongs = 0
            yards_list = furlong_list[0].split(r'*y')

        if len(yards_list) > 1:
            yards = int(yards_list[0].strip())
        else:
            yards = 0

        return (miles * 1760) + (furlongs * 220)
    except:
        import ipdb
        ipdb.set_trace()


def raw_type(race_type):
    return " ".join(race_type.split()[1:])


def raw_distance(race_type):
    return race_type.split()[0]


def prepare_dataframe(df, row):

    df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d')
    df['weekday'] = pd.to_datetime(df['date']).dt.weekday  # Extracting Weekday from each Date
    df = df.dropna(subset=['race_type'])
    df['raw_type'] = df.apply(lambda x: raw_type(x['race_type']), axis=1)
    df['raw_distance'] = df.apply(lambda x: raw_distance(x['race_type']), axis=1)
    df['distance'] = df.apply(lambda x: distance_in_yards(x['raw_distance']), axis=1)

    for i in range(1, 6):
        df[f'race-{i}'] = pd.to_numeric(df[f'race-{i}'], errors='coerce')
        df[f'adv1-{i}'] = pd.to_numeric(df[f'adv1-{i}'], errors='coerce')
        df[f'adv2-{i}'] = pd.to_numeric(df[f'adv2-{i}'], errors='coerce')

    df['timeform'] = df['timeform'].fillna(row['timeform'])  # Assigning '4' to empty TimeForms

    df = df.dropna(subset=['oddschecker'])
    df = df.dropna(subset=['betfair_back'])

    df = df[df['started'] <= row['start_filter']]  # Filtering only favourite horse of each race

    df['best_position'] = df[['race-1', 'race-2', 'race-3', 'race-4', 'race-5']].min(axis=1)
    df['best_position'].fillna(20, inplace=True)

    df['best_position_adv1'] = df[['adv1-1', 'adv1-2', 'adv1-3', 'adv1-4', 'adv1-5']].min(axis=1)
    df['best_position_adv1'].fillna(20, inplace=True)

    df['best_position_adv2'] = df[['adv2-1', 'adv2-2', 'adv2-3', 'adv2-4', 'adv2-5']].min(axis=1)
    df['best_position_adv2'].fillna(20, inplace=True)

    df['won_last_race'] = df.apply(lambda x: is_winner(x['race-1']), axis=1)
    df['won_last_race_adv1'] = df.apply(lambda x: is_winner(x['adv1-1']), axis=1)
    df['won_last_race_adv2'] = df.apply(lambda x: is_winner(x['adv2-1']), axis=1)

    # df['betfair_lay'] = df['betfair_lay'].fillna(1000)
    # df['city'] = LabelEncoder().fit_transform(df['city'])

    return df


def strategy(result):
    if result > 10:
        return result
    else:
        return 0


def going(going):
    replace_dict = {
        "standard to slow": "standard",
        "chase course: good": "good",
        "chase course: soft to heavy, hurdles course: soft": "soft",
        "chase course: good, hurdles course: good to soft": "good",
        "chase course: heavy, hurdles course: soft to heavy": "heavy",
        "chase course: good to soft": "good to soft",
        "chase course: soft": "soft"
    }

    return replace_dict.get(going, going)

def race_type(race, race_type):
    if race.lower() in race_type.lower().split():
        return 1
    else:
        return 0


def prepare_new_dataset(df):
    # Preparing features
    df['weekday'] = pd.to_datetime(df['date']).dt.weekday  # Extracting Weekday from each Date

    df = df.dropna(subset=['race_type']).sort_values(by=['date', 'time', 'city', 'started'], ignore_index=True)
    df['raw_type'] = df.apply(lambda x: raw_type(x['race_type']), axis=1)
    df['raw_distance'] = df.apply(lambda x: raw_distance(x['race_type']), axis=1)
    df['maiden'] = df.apply(lambda x: race_type('mdn', x['race_type']), axis=1)
    df['handicap'] = df.apply(lambda x: race_type('hcap', x['race_type']), axis=1)
    df['stakes'] = df.apply(lambda x: race_type('stks', x['race_type']), axis=1)

    df['distance'] = df.apply(lambda x: distance_in_yards(x['raw_distance']), axis=1)

    for i in range(1, 6):
        df[f'race-{i}'] = pd.to_numeric(df[f'race-{i}'], errors='coerce')
        df[f'adv1-{i}'] = pd.to_numeric(df[f'adv1-{i}'], errors='coerce')
        df[f'adv2-{i}'] = pd.to_numeric(df[f'adv2-{i}'], errors='coerce')

    df['timeform'] = df['timeform'].fillna(4)  # Assigning '4' to empty TimeForms

    df = df.dropna(subset=['oddschecker'])
    # df['oddschecker'] = df['oddschecker'].fillna(value=1000)
    df = df.dropna(subset=['betfair_back'])

    # df = df[df['started'] <= 3]  # Filtering only favourite horse of each race

    df['best_position'] = df[['race-1', 'race-2', 'race-3', 'race-4', 'race-5']].min(axis=1)
    df['best_position_adv1'] = df[['adv1-1', 'adv1-2', 'adv1-3', 'adv1-4', 'adv1-5']].min(axis=1)
    df['best_position_adv2'] = df[['adv2-1', 'adv2-2', 'adv2-3', 'adv2-4', 'adv2-5']].min(axis=1)

    df = df.dropna(subset=['best_position'])
    df = df.dropna(subset=['best_position_adv1'])
    df = df.dropna(subset=['best_position_adv2'])

    # df['best_position'] = df['best_position'].fillna(value=99)
    # df['best_position_adv1'] = df['best_position_adv1'].fillna(value=99)
    # df['best_position_adv2'] = df['best_position_adv2'].fillna(value=99)

    df['won_last_race'] = df.apply(lambda x: is_winner(x['race-1']), axis=1)
    df['won_last_race_adv1'] = df.apply(lambda x: is_winner(x['adv1-1']), axis=1)
    df['won_last_race_adv2'] = df.apply(lambda x: is_winner(x['adv2-1']), axis=1)

    df['jockey_won_last_15_days'] = df['jockey_won_last_15_days'].fillna(0)
    df['jockey_won_yesterday'] = df['jockey_won_yesterday'].fillna(0)
    df = df.drop_duplicates().sort_values(by=['date', 'time', 'city', 'started'], ignore_index=True)

    return df


def place_bet_income(income_pred):
    return 1 if income_pred > 0.5 else 0


def place_bet(win_chance):
    return 1 if win_chance > 0.5 else 0


def place_bet_2(df, index, win_chance):
    try:
        if df.loc[index, 'time'] == df.loc[index + 1, 'time']:
            if df.loc[index, 'win_chance'] - df.loc[index + 1, 'win_chance'] > 0.4:
                return 1
        return 0

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def new_strategy(df):

    # df.sort_values(by=['date', 'city', 'time', 'loose_chance'], inplace=True, ignore_index=True)

    # count = 0
    # for index, column in df.iterrows():
    #     try:
    #         if df.loc[index, 'time'] == df.loc[index + 1, 'time']:
    #             count += 1
    #         else:
    #             count = 0
    #
    #         # if count == 1:
    #         #     if 0.2 < column['win_chance'] <= 0.5 and column['betfair_back'] > 3:
    #         #         df.loc[index, 'winner_pred'] = 1
    #         #         df.loc[index + 1, 'winner_pred'] = 1
    #     except:
    #         pass

    df = df[df['winner_pred'] == 1]
    # df = df[df['won_last_race'] == 0]
    # df = df[df['best_position'] > 1]
    # df = df[df['best_position'] < 99]
    # df = df[df['best_position_adv1'] > 1]
    # df = df[df['jockey_won_yesterday'] == 0]
    # df = df[df['started'] <= 1]
    # df = df[df['horses_race'] < 10]
    # # df = df[df['odds'] > 1.00]
    # df = df.drop_duplicates(subset=['date', 'time', 'city'], keep='last')

    return df


def acerto(winner, winner_pred):
    if winner == 1 and winner_pred == 1:
        return 1
    else:
        return 0


def horse_last_results(df_history, horse, date, i):
    df = df_history[(df_history['horse'] == horse) & (df_history['date'] < date)]
    df.reset_index(inplace=True)
    try:
        return df.loc[len(df) - i, 'finished_int']
    except:
        return 99


def odds(text):
    text = text.split()[0]
    text = text.replace("Evens", "1/1")
    text = text.replace("-", "1000/1")
    text = text.replace("f", "")
    int(text.split('/')[0])
    return int(text.split('/')[0]) / int(text.split('/')[1])


def jockey_last_x_days(df_history, jockey, date, days):
    if not pd.isnull(jockey):
        start_date = date - timedelta(days)
        end_date = date
        df = df_history[
            (df_history['jockey'] == jockey) & (df_history['date'] >= start_date) & (df_history['date'] < end_date)]

        return df['winner'].max() if len(df) else 0

    else:
        return 0


def adv(df, index, started):
    try:
        if started == 1:
            return df.loc[index + 1, 'horse']
        else:
            return df.loc[index - started + 1, 'horse']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def odd_adv(df, index, started):
    try:
        if started == 1:
            return df.loc[index + 1, 'odds']
        else:
            return df.loc[index - started + 1, 'odds']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def race_adv(df, index, started, i):
    try:
        if started == 1:
            return df.loc[index + 1, f'race-{i}']
        else:
            return df.loc[index - started + 1, f'race-{i}']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def race_adv2(df, index, started, i):
    try:
        if started == 1:
            return df.loc[index + 2, f'race-{i}']
        if started == 2:
            return df.loc[index + 1, f'race-{i}']
        else:
            return df.loc[index - started + 2, f'race-{i}']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def adv2(df, index, started):
    try:
        if started == 1:
            return df.loc[index + 2, 'horse']
        if started == 2:
            return df.loc[index + 1, 'horse']
        else:
            return df.loc[index - started + 2, 'horse']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def odd_adv2(df, index, started):
    try:
        if started == 1:
            return df.loc[index + 2, 'odds']
        if started == 2:
            return df.loc[index + 1, 'odds']
        else:
            return df.loc[index - started + 2, 'odds']

    except Exception as e:
        print(f'Erro na linha {index}: {e}')


def started(df, index, time):
    try:
        if time == df.loc[index - 1, 'time']:
            return df.loc[index - 1, 'started'] + 1
    except:
        return 1


def betting_house(column):
    try:
        return float(column[11].replace('', '0'))
    except:
        return 0


def find_jockey(df_history, horse, jockey):
    try:
        if pd.isnull(jockey):
            return jockey
        else:
            jockey = jockey.replace(".", "")
            new_df = df_history[df_history['horse'] == horse]
            new_df.dropna(subset=['jockey'], inplace=True)
            new_df.sort_values(by=['date'], ascending=False, ignore_index=True, inplace=True)
            for index, column in new_df.iterrows():
                if column['jockey'][-3] == jockey[-3]:
                    return column['jockey']
            return jockey
    except:
        import ipdb
        ipdb.set_trace()


def prepare_bbc_dataset(df, df_history, pre_race=False):
    df['date'] = pd.to_datetime(df['date'])
    df_history['date'] = pd.to_datetime(df_history['date'])

    # Odds
    df.rename(columns={"oddschecker": "odds"}, errors="ignore", inplace=True)
    df = df.dropna(subset=['odds'])
    df.reset_index(inplace=True, drop=True)

    if not pre_race:
        df['odds'] = df.apply(lambda row: odds(row['odds']), axis=1)
        df = df[df['odds'] < 1000]
    else:
        if 'going' not in df:
            df['going'] = 'standard'

        df['going'] = df.apply(lambda x: going(x['going']), axis=1)

        df = df[df['betfair_back'] < 999]

        new_df = df['odd_list'].str.split(pat=r"\[|\]|, ", expand=True, n=25)
        new_df.fillna('0', inplace=True)

        # df['odds'] = new_df.apply(lambda x: betting_house(x), axis=1)
        df['odds'] = new_df[11].fillna('0').replace('', '0').astype('float32')
        df['jockey'] = df.apply(lambda x: find_jockey(df_history, x['horse'], x['jockey']), axis=1)

    df.reset_index(drop=True, inplace=True)

    df.sort_values(by=['date', 'city', 'time', 'odds'], ignore_index=True, inplace=True)

    # Started
    count = 1
    for index, row in df.iterrows():
        df.loc[index, 'started'] = count
        try:
            if not (row['city'] == df.loc[index + 1, 'city'] and row['time'] == df.loc[index + 1, 'time'] and row['date'] == df.loc[index + 1, 'date']):
                for i in range(count):
                    df.loc[index - count + i + 1, 'horses_race'] = count

                count = 1

            else:
                count += 1
        except:
            for i in range(count):
                df.loc[index - count + i + 1, 'horses_race'] = count

            count = 1

    #     if index % 10000 == 0:
    #         print(index)
    #
    # df.to_csv(os.path.join(BASES_DIR, 'base_bbc_full_v2.csv'), index=False)

    if not pre_race:
        # Finished
        df.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
        df['finished_int'] = df.apply(lambda x: finishing_position(x['finished'], x['horses_race']), axis=1)

        # Winner
        df['winner'] = df.apply(lambda x: is_winner(x['finished']), axis=1)

    df.sort_values(by=['date', 'city', 'time', 'started'], ignore_index=True, inplace=True)
    df[f'adv1'] = df.apply(lambda x: adv(df, x.name, x.started), axis=1)
    df[f'adv1_odd'] = df.apply(lambda x: odd_adv(df, x.name, x.started), axis=1)

    df[f'adv2'] = df.apply(lambda x: adv2(df, x.name, x.started), axis=1)
    df[f'adv2_odd'] = df.apply(lambda x: odd_adv2(df, x.name, x.started), axis=1)

    # Horse's last results
    df_history.sort_values(by=['horse', 'date'], ignore_index=True, inplace=True)
    for i in range(1, 6):
        df[f'race-{i}'] = df.apply(lambda x: horse_last_results(df_history, x.horse, x.date, i), axis=1)

    for i in range(1, 6):
        df[f'adv1-{i}'] = df.apply(lambda x: race_adv(df, x.name, x.started, i), axis=1)

    for i in range(1, 6):
        df[f'adv2-{i}'] = df.apply(lambda x: race_adv2(df, x.name, x.started, i), axis=1)

    # # Best positions & Won Last Races
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

    # Jockey's last results
    df_history.sort_values(by=['jockey', 'date'], ignore_index=True, inplace=True)

    df['jockey_won_yesterday'] = df.apply(lambda x: jockey_last_x_days(df_history, x.jockey, x.date, 1), axis=1)
    df['jockey_won_last_15_days'] = df.apply(lambda x: jockey_last_x_days(df_history, x.jockey, x.date, 15), axis=1)

    return df


def prepare_model_dataset(df, run=False, le=None):

    df['race-1'].fillna(99, inplace=True)
    df['adv1-1'].fillna(99, inplace=True)
    df['adv2-1'].fillna(99, inplace=True)
    df['best_position'].fillna(99, inplace=True)
    df['best_position_adv1'].fillna(99, inplace=True)
    df['best_position_adv2'].fillna(99, inplace=True)
    position_replace = {99: 20}

    df.replace({'best_position': position_replace,
                'best_position_adv1': position_replace,
                'best_position_adv2': position_replace,
                'race-1': position_replace,
                'adv1-1': position_replace,
                'adv2-1': position_replace})

    if 'going' not in df:
        df['going'] = 'standard'
    else:
        df.dropna(subset=['going'], inplace=True)
        df['going'] = df['going'].str.lower()
        df.reset_index(drop=True, inplace=True)

    if not le:
        le = LabelEncoder()
        le.fit(df['going'].unique())

    df['going'] = le.transform(df['going'])

    if run:
        df['distance_int'] = df.apply(lambda x: distance_in_yards(x.race_type), axis=1)
        df['hurdle'] = df.apply(lambda x: race_category(x.race_type, 'hrd'), axis=1)
        df['chase'] = df.apply(lambda x: race_category(x.race_type, 'chs'), axis=1)
        df['stakes'] = df.apply(lambda x: race_category(x.race_type, 'stks'), axis=1)
        df['handicap'] = df.apply(lambda x: race_category(x.race_type, 'hcap'), axis=1)
        df['novice'] = df.apply(lambda x: race_category(x.race_type, 'nov'), axis=1)

    else:
        df['distance_int'] = df.apply(lambda x: distance_bbc(x.distance), axis=1)
        df['hurdle'] = df.apply(lambda x: race_category(x.title, 'hurdle'), axis=1)
        df['chase'] = df.apply(lambda x: race_category(x.title, 'chase'), axis=1)
        df['stakes'] = df.apply(lambda x: race_category(x.title, 'stakes'), axis=1)
        df['handicap'] = df.apply(lambda x: race_category(x.title, 'handicap'), axis=1)
        df['novice'] = df.apply(lambda x: race_category(x.title, 'novice'), axis=1)

        df['betfair_back'] = df['odds'] + 1

        df['income'] = df.apply(lambda row: financial_result(CONSERVADOR,
                                                             row['betfair_back'],
                                                             row['winner']),
                                axis=1)

    df['adv1_odd'] = df['adv1_odd'] - df['odds']
    df['adv2_odd'] = df['adv2_odd'] - df['odds']

    df = df[df['started'] <= 5]

    return df, le
