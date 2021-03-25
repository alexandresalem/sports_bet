import gc
import os
import pickle
from datetime import datetime, timedelta

import pandas as pd
from sklearn import preprocessing
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR

from horse.constants import MODELOS_DIR, BASES_DIR, HISTORICAL_BASES_DIR, BETS_DIR, ODDFAIR_DIR, CONSERVADOR, BBC_DIR, \
    BBC_PICKLE_DIR
from horse.utils import logger, place_bet_income
from horse.utils import financial_result_model, place_bet, acerto, prepare_model_dataset


def build_new_model(test=True, clf=None):

    # Opening Historical Database
    historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
    df = pd.read_csv(historical_filename, low_memory=False, parse_dates=['date'])
    df, _ = prepare_model_dataset(df)

    # Opening Model Customizing Spreasheet
    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)
    for index, column in df_models.iterrows():

        # Checking if moldel already exists
        if pd.isnull(column["lucro_teste"]):
            features = column['features'].replace(',', '').split()
            features_scaled = [f'{feature}_scaled' for feature in features]
            df.dropna(subset=features, inplace=True)
            df.reset_index(drop=True, inplace=True)

            if test:
                # List all the months in the dataset
                years = df['date'].dt.year.unique()

                for year in years[-1:]:
                    result_folder = os.path.join(MODELOS_DIR, 'predictions')
                    train_result_name = f'novo_{column["name"]}_build_train_{year}.csv'
                    scaled_train_result_name = f'scaled_{column["name"]}_build_train_{year}.csv'
                    test_result_name = f'novo_{column["name"]}_build_test_{year}.csv'
                    scaled_test_result_name = f'scaled_{column["name"]}_build_test_{year}.csv'
                    # train_result_path = os.path.join(result_folder, train_result_name)

                    scaled_train_result_path = os.path.join(result_folder, scaled_train_result_name)
                    test_result_path = os.path.join(result_folder, test_result_name)
                    scaled_test_result_path = os.path.join(result_folder, scaled_test_result_name)

                    df_train = df[(df['date'].dt.year != year) & (df['date'].dt.year != years[0])]
                    df_train.reset_index(drop=True, inplace=True)
                    X_train = df_train[features]

                    std_scaler = preprocessing.StandardScaler()
                    std_scaler.fit(X_train)
                    X_train_scaled = std_scaler.transform(X_train)
                    df_train_scaled = pd.DataFrame(X_train_scaled, columns=features_scaled)
                    X_train_export = pd.concat([df_train, df_train_scaled], axis=1)
                    X_train_export.to_csv(scaled_train_result_path, index=False)

                    df_test = df[(df['date'].dt.year == year)]
                    df_test = df_test[df_test['started'] <= column['started']]
                    df_test = df_test[df_test['odds'] > column['odds']]
                    df_test.reset_index(drop=True, inplace=True)

                    X_test = df_test[features]

                    X_test_scaled = std_scaler.transform(X_test)
                    df_test_scaled = pd.DataFrame(X_test_scaled)

                    y_train = df_train[column["label"]]

                    model_folder = os.path.join(MODELOS_DIR, 'novos')
                    model_name = f'{column["name"]}_{year}.model'
                    model_path = os.path.join(model_folder, model_name)
                    try:
                        clf = pickle.load(open(model_path, 'rb'))
                        logger.info(f'Carregando Modelo: {model_name}')
                        logger.warning((f'Modelo Carregado!'))
                    except:
                        print(f'Criando Modelo: {model_name}')
                        if column['type'] == "RandomForestClassifier":


                            max_depth = None if column['max_depth'] == 'None' else column['max_depth']
                            clf = RandomForestClassifier(n_estimators=column["estimators"],
                                                         criterion=column['criterion'],
                                                         min_samples_split=column['min_samples_split'],
                                                         min_samples_leaf=column['min_samples_leaf'],
                                                         max_depth=max_depth)


                        elif column['type'] == "KneighborsRegressor":
                            clf = SVR()

                        clf.fit(X_train_scaled, y_train)
                        pickle.dump(clf, open(model_path, 'wb'))
                        print(f'Modelo Criado!')

                    # Starting Prediction

                    if 'Classifier' in column['type']:
                        df_test['winner_pred'] = list(clf.predict(X_test_scaled))
                        df_predict = pd.DataFrame(data=clf.predict_proba(X_test_scaled),
                                                  columns=['loose_chance', 'win_chance'])

                        X_test_export = pd.concat([df_test, df_test_scaled, df_predict], axis=1)
                        X_test_export['place_bet'] = X_test_export.apply(lambda row: place_bet(row['win_chance']), axis=1)
                    else:
                        df_test['income_pred'] = list(clf.predict(X_test_scaled))
                        X_test_export = pd.concat([df_test, df_test_scaled], axis=1)
                        X_test_export['place_bet'] = X_test_export.apply(lambda row: place_bet_income(row['income_pred']),
                                                                           axis=1)

                    X_test_export['income_bets'] = X_test_export.apply(lambda x: financial_result_model(CONSERVADOR, x['betfair_back'], x['winner'], x['place_bet']), axis=1)
                    X_test_export['acerto'] = X_test_export.apply(lambda x: acerto(x['winner'], x['place_bet']), axis=1)
                    X_test_export.to_csv(scaled_test_result_path, index=True)

                    # Writting Results
                    df_models.loc[index, f'lucro_teste_{year}'] = X_test_export['income_bets'].sum()
                    df_models.loc[index, f'apostas_teste_{year}'] = X_test_export['place_bet'].sum()
                    df_models.loc[index, f'acertos_teste_{year}'] = round(X_test_export['acerto'].sum()/X_test_export['place_bet'].sum(),4)

                    df_models.to_csv(models, index=False)


def run_new_model(date_string, clf=None, days=1, racing_hours=False):
    models = os.path.join(MODELOS_DIR, 'models.csv')
    df_models = pd.read_csv(models)

    for index, column in df_models.iterrows():

        if not pd.isnull(column["use"]):
            start = datetime.now()
            logger.info(f'Modelagem: Preparando as bases para rodar o {column["name"]} para o dia {date_string}')

            files = os.listdir(os.path.join(BASES_DIR, ODDFAIR_DIR))

            date_list = [(datetime.strptime(date_string, '%Y.%m.%d') - timedelta(days=x)).strftime('%Y.%m.%d')
                         for x in range(days)]

            files_list = []

            ext = '' if racing_hours else '_v1'

            for day in date_list:
                if f'base_pre_race_{day}{ext}.csv' in files:
                    files_list.append(os.path.join(BASES_DIR,
                                                   ODDFAIR_DIR,
                                                   f'base_pre_race_{day}{ext}.csv'))

            if len(files_list):
                df_predict = pd.concat([pd.read_csv(file, parse_dates=['date']) for file in files_list],
                                       axis=0,
                                       join='inner').sort_values(by=['date', 'city', 'time'])

                # daily_races = os.path.join(BASES_DIR, ODDFAIR_DIR, f'base_pre_race_{date_string}.csv')
                # df_predict = pd.read_csv(daily_races, parse_dates=['date'])

                if racing_hours or f'base_bbc_{date_string}.pickle' in os.listdir(os.path.join(BASES_DIR, BBC_PICKLE_DIR)):
                    with open(os.path.join(BASES_DIR, BBC_PICKLE_DIR, f'label_encoder_{date_string}.pickle'), 'rb') as handle:
                        le = pickle.load(handle)

                    df_history = pd.read_pickle(os.path.join(BASES_DIR, BBC_PICKLE_DIR, f'base_bbc_{date_string}.pickle'))
                else:
                    historical_filename = os.path.join(BASES_DIR, f'base_bbc_full.csv')
                    df_history = pd.read_csv(historical_filename, low_memory=False, parse_dates=['date'])
                    df_history, le = prepare_model_dataset(df_history)

                    df_history.to_pickle(os.path.join(BASES_DIR, BBC_PICKLE_DIR, f'base_bbc_{date_string}.pickle'))
                    with open(os.path.join(BASES_DIR, BBC_PICKLE_DIR, f'label_encoder_{date_string}.pickle'), 'wb') as handle:
                        pickle.dump(le, handle)

                df_predict, _ = prepare_model_dataset(df_predict, run=True, le=le)
                logger.info(f'Modelagem: Base do dia {date_string} preparada em {datetime.now() - start} segundos')

                features = column['features'].replace(',', '').split()
                features_scaled = [f'{feature}_scaled' for feature in features]
                df_history.dropna(subset=features, inplace=True)

                years = df_history['date'].dt.year.unique()
                df_history = df_history[(df_history['date'].dt.year != years[0]) & (df_history['date'].dt.year != years[-1])]
                df_history.reset_index(drop=True, inplace=True)

                X_train = df_history[features]
                std_scaler = preprocessing.StandardScaler()
                std_scaler.fit(X_train)

                # VERIFICACAO SE O SCALE ESTA FUNCIONANDO
                # X_train_scaled = std_scaler.transform(X_train)
                # df_train_scaled = pd.DataFrame(X_train_scaled, columns=features_scaled)
                # X_train_export = pd.concat([df_history, df_train_scaled], axis=1)
                # scaled_train_result_name = f'scaled_{column["name"]}_run_train_{years[-1]}.csv'
                # scaled_test_result_name = f'scaled_{column["name"]}_run_test_{date_string}.csv'
                # result_folder = os.path.join(MODELOS_DIR, 'predictions')
                # scaled_train_result_path = os.path.join(result_folder, scaled_train_result_name)
                # scaled_test_result_path = os.path.join(result_folder, scaled_test_result_name)
                # X_train_export.to_csv(scaled_train_result_path, index=False)

                df_predict.dropna(subset=features, inplace=True)
                df_predict = df_predict[df_predict['started'] <= column['started']]
                df_predict = df_predict[df_predict['odds'] > column['odds']]
                df_predict.reset_index(drop=True, inplace=True)

                X_pred = df_predict[features]
                X_pred_scaled = std_scaler.transform(X_pred)
                df_pred_scaled = pd.DataFrame(X_pred_scaled, columns=features_scaled)

                del df_history
                gc.collect()

                try:
                    start = datetime.now()
                    logger.info(f'Loading {column["name"]} for {date_string}')
                    clf = pickle.load(
                        open(os.path.join(MODELOS_DIR, 'novos', f'{column["name"]}_2021.model'), 'rb'))
                    logger.info(f'O {column["name"]} levou {datetime.now() - start} segundos para carregar')

                    logger.info(f'Rodando Modelo: Started Model {column["name"]} Prediction for {date_string}')
                    df_results = pd.DataFrame(data=clf.predict_proba(X_pred_scaled), columns=['loose_chance', 'win_chance'])

                    del clf
                    gc.collect()

                    X_pred_export = pd.concat([df_predict, df_pred_scaled, df_results], axis=1)
                    X_pred_export['winner_pred'] = X_pred_export.apply(lambda row: place_bet(row['win_chance']), axis=1)
                    # X_pred_export.to_csv(scaled_test_result_path, index=True)

                    if days == 1:
                        filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}{ext}.csv')
                    else:
                        filename = os.path.join(BASES_DIR, BETS_DIR, f'aposta_{column["name"]}_{date_string}_days_{days}{ext}.csv')

                    X_pred_export.drop_duplicates(subset=['date', 'time', 'city', 'horse'], inplace=True, keep='last')
                    X_pred_export.to_csv(filename, index=False)
                    logger.info(f'Rodando Modelo: Apostas do {column["name"]} para o dia {date_string} salvas com sucesso!')
                except Exception as e:
                    logger.warning(e)

            else:
                logger.warning(f'Pre-race: Não existe base para o dia {date_string}')
