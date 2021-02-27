import os
import pickle
from datetime import datetime, timedelta

import pandas as pd
import torch
from sklearn import preprocessing
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from torch import nn, optim
from torch.utils.data import Dataset, DataLoader

from horse.constants import MODELOS_DIR, BASES_DIR, HISTORICAL_BASES_DIR, BETS_DIR, ODDFAIR_DIR, AGRESSIVO, MEDIANO, \
    CONSERVADOR
from horse.utils import financial_result, distance_in_yards, finishing_position, prepare_dataframe, is_winner, \
    financial_result_model, prepare_new_dataset, place_bet, acerto, prepare_model_dataset


class Model:
    def __init__(self, name, date):
        self.name = name
        self.date = date

        # Loading and preparing historical datababse before running model
        historical_filename = os.path.join(BASES_DIR, HISTORICAL_BASES_DIR, f'base_historica_{date_string}.csv')

    def train(self, monthly=False):

        pass

    def predict(self):
        pass

    def evaluate(self):
        pass


def build_new_model(test=True, clf=None):

    historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
    df = pd.read_csv(historical_filename, low_memory=False, parse_dates=['date'])

    df, _ = prepare_model_dataset(df)

    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)

    for index, column in df_models.iterrows():

        if pd.isnull(column["lucro_teste"]):
            features = column['features'].replace(',', '').split()
            df.dropna(subset=features, inplace=True)
            df = df[df['started'] <= column['started']]
            df = df[df['odds'] > column['odds']]
            df.reset_index(drop=True, inplace=True)

            if test:
                # List all the months in the dataset
                years = df['date'].dt.year.unique()

                for year in years[-2:]:

                    result_folder = os.path.join(MODELOS_DIR, 'predictions')
                    train_result_name = f'novo_{column["name"]}_final_train_{year}.csv'
                    test_result_name = f'novo_{column["name"]}_final_test_{year}.csv'
                    train_result_path = os.path.join(result_folder, train_result_name)
                    test_result_path = os.path.join(result_folder, test_result_name)

                    df_train = df[df['date'].dt.year != year]
                    df_test = df[df['date'].dt.year == year]

                    X_train = df_train[features]
                    X_test = df_test[features]

                    X_final = pd.concat([X_train, X_test], axis=0)

                    min_max_scaler = preprocessing.MinMaxScaler().fit(X_final)

                    X_train_scaled = min_max_scaler.transform(X_train)
                    X_test_scaled = min_max_scaler.transform(X_test)


                    y_train = df_train[column["label"]]

                    model_folder = os.path.join(MODELOS_DIR, 'novos')
                    model_name = f'{column["name"]}_{year}.model'
                    model_path = os.path.join(model_folder, model_name)
                    try:
                        clf = pickle.load(open(model_path, 'rb'))
                        print(f'Carregando Modelo: {model_name}')
                        print(f'Modelo Carregado!')

                    except:
                        print(f'Criando Modelo: {model_name}')
                        # clf = SVC()

                        max_depth = None if column['max_depth'] == 'None' else column['max_depth']

                        clf = RandomForestClassifier(n_estimators=column["estimators"],
                                                     criterion=column['criterion'],
                                                     min_samples_split=column['min_samples_split'],
                                                     min_samples_leaf=column['min_samples_leaf'],
                                                     max_depth=max_depth)
                        clf.fit(X_train_scaled, y_train)
                        pickle.dump(clf, open(model_path, 'wb'))
                        print(f'Modelo Criado!')


                    # Starting Prediction
                    df_test.reset_index(inplace=True, drop=True)
                    df_test['winner_pred'] = list(clf.predict(X_test_scaled))
                    df_predict = pd.DataFrame(data=clf.predict_proba(X_test_scaled),
                                              columns=['loose_chance', 'win_chance'])
                    df_test['win_chance'] = df_predict['win_chance'].values.tolist()
                    df_test['loose_chance'] = df_predict['loose_chance'].values.tolist()
                    df_test['income'] = df_test.apply(lambda x: financial_result_model(CONSERVADOR, x['betfair_back'], x['winner'], x['winner_pred']), axis=1)
                    df_test['acerto'] = df_test.apply(lambda x: acerto(x['winner'], x['winner_pred']), axis=1)
                    df_test.to_csv(test_result_path, index=False)

                    # df_train.reset_index(inplace=True)
                    # df_train['winner_pred'] = list(clf.predict(X_train_scaled))
                    # df_predict = pd.DataFrame(data=clf.predict_proba(X_train_scaled), columns=['loose_chance', 'win_chance'])
                    # df_train['win_chance'] = df_predict['win_chance'].values.tolist()
                    # df_train['loose_chance'] = df_predict['loose_chance'].values.tolist()
                    # df_train['income'] = df_train.apply(lambda x: financial_result_model(CONSERVADOR, x['oddschecker'], x['winner'], x['winner_pred']), axis=1)
                    # df_train['acerto'] = df_train.apply(lambda x: acerto(x['winner'], x['winner_pred']), axis=1)
                    # df_train.to_csv(train_result_path, index=False)

                    # Writting Results
                    df_models.loc[index, f'lucro_teste_{year}'] = df_test['income'].sum()
                    df_models.loc[index, f'apostas_teste_{year}'] = df_test['winner_pred'].sum()
                    df_models.loc[index, f'acertos_teste_{year}'] = round(df_test['acerto'].sum()/df_test['winner_pred'].sum(),4)

                    # df_models.loc[index, 'lucro_treino'] = df_train['income'].sum()
                    # df_models.loc[index, 'apostas_treino'] = df_train['winner_pred'].sum()
                    # df_models.loc[index, 'acertos_treino'] = round(df_train['acerto'].sum() / df_train['winner'].sum(), 2)

                    df_models.to_csv(models, index=False)


def run_new_model(date_string, clf=None):

    historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
    df_history = pd.read_csv(historical_filename, low_memory=False, parse_dates=['date'])
    df_history, le = prepare_model_dataset(df_history)
    df_history.dropna(subset=['horses_race', 'adv2_odd'], inplace=True)

    df_history.reset_index(drop=True, inplace=True)

    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)

    for index, column in df_models.iterrows():

        if not pd.isnull(column["use"]):

            features = column['features'].replace(',', '').split()
            df_history.dropna(subset=features, inplace=True)
            df_history = df_history[df_history['started'] <= column['started']]
            df_history = df_history[df_history['odds'] > column['odds']]
            df_history.reset_index(drop=True, inplace=True)

            X_train = df_history[features]

            min_max_scaler = preprocessing.MinMaxScaler().fit(X_train)
            daily_races = os.path.join(BASES_DIR, ODDFAIR_DIR, f'base_pre_race_{date_string}.csv')
            df_predict = pd.read_csv(daily_races, parse_dates=['date'])
            df_predict, _ = prepare_model_dataset(df_predict, run=True, le=le)

            df_predict.dropna(subset=features, inplace=True)
            df_predict = df_predict[df_predict['started'] <= column['started']]
            df_predict = df_predict[df_predict['odds'] > column['odds']]
            df_predict.reset_index(drop=True, inplace=True)

            X_pred = df_predict[features]

            X_pred_scaled = min_max_scaler.transform(X_pred)

            try:
                start = datetime.now()
                print(f'Loading Model {column["name"]} Prediction for {date_string}')
                clf = pickle.load(
                    open(os.path.join(MODELOS_DIR, 'novos', f'{column["name"]}_2021.model'), 'rb'))
                print(f'O modelo {column["name"]} levou {datetime.now() - start} segundos para carregar')

                print(f'Started Model {column["name"]} Prediction for {date_string}')
                df_results = pd.DataFrame(data=clf.predict_proba(X_pred_scaled), columns=['loose_chance', 'win_chance'])
                df_predict['winner_pred'] = df_results.apply(lambda row: place_bet(row['win_chance']), axis=1)
                df_predict['win_chance'] = df_results['win_chance'].values.tolist()
                df_predict['loose_chance'] = df_results['loose_chance'].values.tolist()

                filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}.csv')
                df_predict.to_csv(filename, index=False)
            except:
                pass

