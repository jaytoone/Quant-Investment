import os
# pwd = os.getcwd()
#
# # print(os.path.dirname(pwd))
# # print(pwd)
# switch_path = os.path.dirname(pwd)
# os.chdir(switch_path)

# from binance_f import RequestClient
# from binance_f.model import *
from binance_f.constant.test import *
# from binance_f.base.printobject import *

from funcs_binance.binance_futures_concat_candlestick_ftr import concat_candlestick

import matplotlib.pyplot as plt

from funcs.funcs_trader import *
from funcs.funcs_indicator import *
import mpl_finance as mf

# import numpy as np
# import pandas as pd

pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 2500)
pd.set_option('display.max_columns', 2500)


def sync_check(df, second_df, third_df, fourth_df, plot_size=45, plotting=False):

    #       mmh_st      #
    # df['tsl'] = mmh_st(df, 5)
    # print(df.tail(40))
    # quit()

    # ----- stdev ----- #
    # df['stdev'] = stdev(df, 20)
    # print(df.stdev.tail(10))
    # quit()

    # ----- atr ----- #
    # df['atr'] = atr(df, 20)
    # print(df.stdev.tail(10))
    # quit()

    # df = dc_line(df, None, '1m', dc_period=20)
    # df = dc_line(df, third_df, '5m')
    # df = dc_line(df, fourth_df, '15m')
    #
    df = bb_line(df, None, '1m')
    # df = bb_line(df, third_df, '5m')
    # df = bb_line(df, fourth_df, '15m')
    # df = bb_line(df, fourth_df, '30m')
    print(df.tail(5)) # 20:15:59.999  3321.18  3321.98  3320.99  3321.74  580.510  3322.939546  3318.316454
    quit()


    start_0 = time.time()


    # third_df['ema_5m'] = ema(third_df['close'], 190)
    # # third_df['ema_5m'] = ema(third_df['close'].values, sma(third_df['close'], 190).values, 190)
    # # third_df['ema_5m'] = sma(third_df['close'], 190)
    # print(third_df['ema_5m'].tail(5))
    # print(time.time() - start_0)
    # quit()
    #
    # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf_v2(df, third_df, [-1]), columns=['ema_5m']))
    # print(df['ema_5m'].tail(20))
    # # print(df.tail(5))
    # # print(df['ema_5m'].loc["2022-01-13 20:19:59.999"])
    # quit()

    # ----- bb ----- #
    # df = bb_line(df, None, '1m')
    # df = bb_level(df, '1m', 1)
    # print(df.iloc[:, -6:].tail(40))
    # quit()

    # # ----- dc ----- #
    # df = dc_line(df, None, '1m')
    # df = dc_level(df, '1m', 1)
    # print(df.iloc[:, -8:].tail(40))
    # quit()

    # ----- rsi ----- #
    df['rsi'] = rma(df['close'], 14)
    # df['rsi'] = rsi(df, 14)
    print(df.rsi.tail(40))
    quit()

    # ----- cci ----- #
    df['cci'] = cci(df, 20)
    print(df.cci.tail(40))
    quit()


    # ----- cloud bline ----- #
    # df['cloud_bline'] = cloud_bline(df, 26)
    # third_df['cloud_bline_5m'] = cloud_bline(third_df, 26)
    # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, third_df, [-1]), columns=['cloud_bline_5m']))
    # print(df.tail(200))
    # quit()
    #
    # #       normal st      #
    # df['st'] = supertrend(df, 5, 6, cal_st=True)
    # print(df.tail(40))
    # quit()

    #           supertrend          #
    df = st_price_line(df, third_df, '5m')
    df = st_level(df, '5m', 0.5)
    print(df.iloc[:, -6:].tail(60))
    quit()

    #
    # # print(df[["minor_ST1_Up", "minor_ST2_Up", "minor_ST3_Up"]].tail())
    # # min_upper = np.minimum(df["minor_ST1_Up"], df["minor_ST2_Up"], df["minor_ST3_Up"])
    # # max_lower = np.maximum(df["minor_ST1_Down"], df["minor_ST2_Down"], df["minor_ST3_Down"])
    # min_upper = np.min(df[["minor_ST1_Up", "minor_ST2_Up", "minor_ST3_Up"]], axis=1)
    # max_lower = np.max(df[["minor_ST1_Down", "minor_ST2_Down", "minor_ST3_Down"]], axis=1)
    #
    # df['middle_line'] = (min_upper + max_lower) / 2
    #
    # #           lucid sar              #
    second_df['sar'] = lucid_sar(second_df)
    # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, second_df, [-1]), columns=['sar1']))
    #
    # # third_df['sar'] = lucid_sar(third_df)
    # # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, third_df, [-1]), columns=['sar2']))
    #
    # fourth_df['sar'] = lucid_sar(fourth_df)
    # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, fourth_df, [-1]), columns=['sar2']))
    #
    # # print(df[['sar1', 'sar2']].tail(20))
    # # quit()
    #
    # #           ichimoku            #
    # # df['senkou_a'], df['senkou_b'] = ichimoku(df)
    #
    # second_df['senkou_a'], second_df['senkou_b'] = ichimoku(second_df)
    # df = df.join( pd.DataFrame(index=df.index, data=to_lower_tf(df, second_df, [-2, -1]), columns=['senkou_a', 'senkou_b']))
    #
    # # third_df['senkou_a'], third_df['senkou_b'] = ichimoku(third_df)
    # # df = df.join( pd.DataFrame(index=df.index, data=to_lower_tf(df, third_df, [-2, -1]), columns=['senkou_a', 'senkou_b']))
    #
    # # fourth_df['senkou_a'], fourth_df['senkou_b'] = ichimoku(fourth_df)
    # # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, fourth_df, [-2, -1]), columns=['senkou_a', 'senkou_b']))
    #
    # #           1-2. displacement           #
    # # df['senkou_a'] = df['senkou_a'].shift(26 - 1)
    # # df['senkou_b'] = df['senkou_b'].shift(26 - 1)
    #
    # df.iloc[:, -2:] = df.iloc[:, -2:].shift(26 - 1)
    #
    # #           macd            #
    # second_df['macd_hist'] = macd(second_df)
    # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, second_df, [-1]), columns=['macd_hist']))
    #
    # # fourth_df['macd_hist'] = macd(fourth_df)
    # # df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, fourth_df, [-1]), columns=['macd_hist']))
    #
    # # print(df['macd_hist'].tail(20))
    # # quit()
    #
    # #          trix         #
    # df['trix'] = trix_hist(df, 14, 1, 5)
    # # print(df['trix'].tail(15))
    # # quit()

    # ------------ ema_roc ------------ #
    df['ema_roc'] = ema_roc(df['close'], 13, 9)

    print(df.iloc[:, -3:].tail(20))
    quit()

    #          stochastic           #
    df['stoch'] = stoch(df)

    #          fisher           #
    df['fisher'] = fisher(df, 30)

    #          cctbbo           #
    df['cctbbo'], _ = cct_bbo(df, 21, 13)

    print(df.iloc[:, -3:].tail(20))
    quit()

    if plotting:

        plot_df = df.iloc[-plot_size:, [0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19]]

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111)

        fig.show()
        fig.canvas.draw()

        temp_ohlc = plot_df.values[:, :4]
        index = np.arange(len(temp_ohlc))
        candle = np.hstack((np.reshape(index, (-1, 1)), temp_ohlc))
        mf.candlestick_ohlc(ax, candle, width=0.5, colorup='r', colordown='b')

        # print(plot_df.values[:, 4:])
        plt.plot(plot_df.values[:, [4, 6, 8]], 'r', alpha=1)  # upper
        plt.plot(plot_df.values[:, [5, 7, 9]], 'b', alpha=1)  # lower
        plt.plot(plot_df.values[:, [10]], 'g', alpha=1)  # middle

        plt.plot(plot_df.values[:, [11]], 'c*', alpha=1, markersize=5)  # sar mic
        plt.plot(plot_df.values[:, [12]], 'co', alpha=1, markersize=7)  # sar mac

        # plt.plot(plot_df.values[:, [13]], 'c', alpha=1)  # senkou a
        # plt.plot(plot_df.values[:, [14]], 'fuchsia', alpha=1)  # senkou b

        plt.fill_between(np.arange(len(plot_df)), plot_df.values[:, 13], plot_df.values[:, 14],
                         where=plot_df.values[:, 13] >= plot_df.values[:, 14], facecolor='g', alpha=0.5)
        plt.fill_between(np.arange(len(plot_df)), plot_df.values[:, 13], plot_df.values[:, 14],
                         where=plot_df.values[:, 13] <= plot_df.values[:, 14], facecolor='r', alpha=0.5)

        plt.show()
        # plt.draw()

        #       plot second plots       #
        plt.plot(plot_df.values[:, [15]], 'g', alpha=1)  # middle
        plt.axhline(0)
        plt.show()

        plt.close()

        # plt.pause(1e-3)

    return df


if __name__=="__main__":

    interval = "1m"
    interval2 = "1d"
    # interval2 = "4h"
    # interval2 = "1d"

    interval3 = "5m"
    interval4 = "15m"
    symbol = "ETHUSDT"
    # symbol = "NEOUSDT"

    # initial = True
    # while 1:

    df, _ = concat_candlestick(symbol, interval, days=1) # 15:05:59.999    3294.704479 15:05:59.999    3294.705970
    # print(df.tail())
    # quit()
    second_df, _ = concat_candlestick(symbol, interval2, days=1)
    # second_df, _ = concat_candlestick(symbol, interval2, days=3) # >= 30m
    # second_df, _ = concat_candlestick(symbol, interval2, days=10) # for 4h
    # second_df, _ = concat_candlestick(symbol, interval2, days=50) # for 1d
    # print(second_df.tail())
    # quit()

    third_df, _ = concat_candlestick(symbol, interval3, days=1, limit=200) # 12:49:59.999    3283.658577    12:49:59.999    3283.658577    3290.392904  14.77669644355774
    fourth_df, _ = concat_candlestick(symbol, interval4, days=1)

    res_df = sync_check(df, second_df, third_df, fourth_df, plotting=True, plot_size=300)


    # print(res_df[["minor_ST1_Up", "minor_ST1_Down"]].tail(50))
    # print(res_df[["minor_ST1_Up", "minor_ST2_Up", "minor_ST3_Up"]].tail(20))
    # print(res_df[["minor_ST1_Down", "minor_ST2_Down", "minor_ST3_Down"]].tail(20))

