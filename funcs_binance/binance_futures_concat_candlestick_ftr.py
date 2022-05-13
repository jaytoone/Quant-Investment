import pandas as pd
import os
from datetime import datetime
from binance_f import RequestClient
from binance_f.model import *
from binance_f.constant.test import *
from binance_f.base.printobject import *
import time

request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)

pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 3000)
pd.set_option('display.max_columns', 2500)


#           1 day = 86399000. (timestamp)       #
a_day = 3600 * 24 * 1000


def concat_candlestick(symbol, interval, days, limit=1500, end_date=None, show_process=False, timesleep=None):

    if end_date is None:
        end_date = str(datetime.now()).split(' ')[0]

    startTime_ = datetime.timestamp(pd.to_datetime('{} 00:00:00'.format(end_date))) * 1000
    
    #       1. trader 에서 자정 지나면 data 부족해지는 문제로 days >= 2 적용    #
    #           1_1. limit under 1500 으로 cover 가능 - starttime = None 이면, 자정 이전 data load 함
    #           1_2. 본인이 직접 위에 startTime 을 자정으로 설정했으니.

    # if interval != '1m':
    if interval == '1d':
        startTime_ -= a_day

    endTime = datetime.timestamp(pd.to_datetime('{} 23:59:59'.format(end_date))) * 1000

    if show_process:
        print(symbol)
        
    if days > 1:    # 1일 이상의 data 가 필요한 경우 limit 없이 모두 가져옴
        limit = 1500

    for day_cnt in range(days):

        if day_cnt != 0:
            startTime_ -= a_day
            endTime -= a_day

        # if show_process:
        #     print(datetime.fromtimestamp(startTime_ / 1000), end=' --> ')
        #     print(datetime.fromtimestamp(endTime / 1000))

        try:
            startTime = int(startTime_)
            endTime = int(endTime)
            #        limit < max_limit, startTime != None 일 경우, last_index 이상하게 나옴        #
            if limit != 1500:
                startTime = None

            df = request_client.get_candlestick_data(symbol=symbol,
                                                     interval=interval,
                                                     startTime=startTime, endTime=endTime, limit=limit)
            if show_process:
                print(df.index[0], end=" --> ")
                print(df.index[-1])
            # print("endTime :", endTime)
            # print(df.tail())
            # quit()

            assert len(df) != 0, "len(df) == 0"

            if day_cnt == 0:
                sum_df = df
            else:
                # print(df.head())
                # sum_df = pd.concat([sum_df, df])
                sum_df = df.append(sum_df)  # <-- -a_day 이기 때문에 sum_df 와 df 의 위치가 좌측과 같다.
                # print(sum_df)
                # quit()

            if timesleep is not None:
                time.sleep(timesleep)

        except Exception as e:
            print('error in get_candlestick_data :', e)

            if len(df) == 0:
                # quit()
                break

    # end_date = str(datetime.fromtimestamp(endTime / 1000)).split(' ')[0]
    # print(len(sum_df[~sum_df.index.duplicated(keep='first')]))

    # keep = 'last' 로 해야 중복기준 최신 df 를 넣는건데, 왜 first 로 해놓은거지
    return sum_df[~sum_df.index.duplicated(keep='last')], end_date


if __name__ == '__main__':

    days = 300
    days = 5

    end_date = "2021-04-12"
    end_date = "2020-09-06"
    end_date = None

    # intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '4h'] - old
    intervals = ['1m']

    concat_path = '../candlestick_concated/database_bn'

    if end_date is None:
        end_date = str(datetime.now()).split(' ')[0]

    save_dir = os.path.join(concat_path, end_date)
    os.makedirs(save_dir, exist_ok=True)

    exist_files = os.listdir(save_dir)

    # with open('../ticker_list/binance_futures_20211207.pkl', 'rb') as f:
    #     coin_list = pickle.load(f)
    # coin_list = ['ETHUSDT', 'BTCUSDT', 'ETCUSDT', 'ADAUSDT', 'XLMUSDT', 'LINKUSDT', 'LTCUSDT', 'EOSUSDT', 'XRPUSDT',
    #              'BCHUSDT']
    coin_list = ['ETHUSDT']
    print(coin_list)

    for coin in coin_list:
        for interval in intervals:
            #       check existing file     #
            #       Todo        #
            #        1. this phase require valid end_date       #
            save_name = '%s %s_%s.ftr' % (end_date, coin, interval)
            # if save_name in exist_files:
            #     print(save_name, 'exist !')
            #     continue

            try:
                concated_df, end_date = concat_candlestick(coin, interval, days, limit=1500,
                                                              end_date=end_date, show_process=True, timesleep=0.2)
                # print(concated_df.tail())
                # quit()
                concated_df.reset_index().to_feather(os.path.join(save_dir, save_name), compression='lz4')
            except Exception as e:
                print('Error in save to_excel :', e)
                continue
