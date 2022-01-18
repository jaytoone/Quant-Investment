from funcs.funcs_indicator import *
from funcs.funcs_trader import *
import logging

sys_log3 = logging.getLogger()


class OrderSide:
    BUY = "BUY"
    SELL = "SELL"
    INVALID = None


def lvrg_set(res_df, config, open_side, ep_, out_, fee, limit_leverage=50):

    strat_version = config.strat_version

    if open_side == OrderSide.SELL:

        if strat_version in ["v3"]:
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / (out_ / ep_ - 1 - (fee + config.trader_set.market_fee))
            config.lvrg_set.leverage = config.lvrg_set.target_pct / (
                        out_ / ep_ - 1 - (fee + config.trader_set.market_fee))

            #     zone 에 따른 c_ep_gap 를 고려 (loss 완화 방향) / 윗 줄은 수익 극대화 방향
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / (out_ / res_df['short_ep_org'].iloc[ep_j] - 1 - (fee + config.trader_set.market_fee))

        elif strat_version in ["v5_2", "v7_3"]:
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(ep_ / out_ - 1 - (fee + config.trader_set.market_fee))
            config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(
                ep_ / out_ - 1 - (fee + config.trader_set.market_fee))
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(res_df['short_ep_org'].iloc[ep_j] / out_ - 1 - (fee + config.trader_set.market_fee))

    else:
        #   윗 phase 는 min_pr 의 오차가 커짐
        if strat_version in ["v3"]:
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / (ep_ / out_ - 1 - (fee + config.trader_set.market_fee))
            config.lvrg_set.leverage = config.lvrg_set.target_pct / (
                        ep_ / out_ - 1 - (fee + config.trader_set.market_fee))
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / (res_df['long_ep_org'].iloc[ep_j] / out_ - 1 - (fee + config.trader_set.market_fee))

        elif strat_version in ["v5_2", "v7_3"]:
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(out_ / ep_ - 1 - (fee + config.trader_set.market_fee))
            config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(
                out_ / ep_ - 1 - (fee + config.trader_set.market_fee))
            # config.lvrg_set.leverage = config.lvrg_set.target_pct / abs(out_ / res_df['long_ep_org'].iloc[ep_j] - 1 - (fee + config.trader_set.market_fee))

    if not config.lvrg_set.allow_float:
        config.lvrg_set.leverage = int(config.lvrg_set.leverage)

    # -------------- leverage rejection -------------- #
    if config.lvrg_set.leverage < 1 and config.lvrg_set.lvrg_rejection:
        return None

    config.lvrg_set.leverage = max(config.lvrg_set.leverage, 1)

    config.lvrg_set.leverage = min(limit_leverage, config.lvrg_set.leverage)

    return config.lvrg_set.leverage


def sync_check(res_df_list, order_side="OPEN"):

    df, third_df, fourth_df = res_df_list

    #       add indi. only      #

    #       Todo : manual        #
    #        1. 필요한 indi. 는 enlist_epouttp & mr_check 보면서 삽입
    #        2. htf use_rows 는 1m use_rows 의 길이를 만족시킬 수 있는 정도
    #         a. 1m use_rows / htf_interval 하면 대략 나옴
    #         b. 또한, htf indi. 를 생성하기 위해 필요한 최소 row 이상
    df = dc_line(df, None, '1m', dc_period=20)
    df = bb_line(df, None, '1m')
    df = bb_line(df, third_df, '5m')
    df = dc_line(df, third_df, '5m')
    df = bb_line(df, fourth_df, '15m')
    df = dc_line(df, fourth_df, '15m')

    df['rsi_1m'] = rsi(df, 14)

    if order_side in ["OPEN"]:

        third_df['ema_5m'] = ema(third_df['close'], 195)
        df = df.join(pd.DataFrame(index=df.index, data=to_lower_tf(df, third_df, [-1]), columns=['ema_5m']))

    return df


def public_indi(res_df, order_side="OPEN"):

    res_df = bb_level(res_df, '5m', 1)
    res_df = dc_level(res_df, '5m', 1)
    res_df = bb_level(res_df, '15m', 1)
    res_df = dc_level(res_df, '15m', 1)
    # res_df = bb_level(res_df, '30m', 1)
    # res_df = dc_level(res_df, '30m', 1)

    if order_side in ["OPEN"]:

        res_df["candle_ratio"], res_df['body_ratio'] = candle_ratio(res_df)

        start_0 = time.time()

        h_c_intv1 = 15
        h_c_intv2 = 60
        res_df = h_candle(res_df, h_c_intv1)
        res_df = h_candle(res_df, h_c_intv2)
        h_candle_col = ['hopen_{}'.format(h_c_intv2), 'hhigh_{}'.format(h_c_intv2), 'hlow_{}'.format(h_c_intv2), 'hclose_{}'.format(h_c_intv2)]

        res_df['h_candle_ratio'], res_df['h_body_ratio'] = candle_ratio(res_df, ohlc_col=h_candle_col, unsigned=0)

        # sys_log3.warning("~ h_candle_ratio elapsed time : {}".format(time.time() - start_0))

    #     temp indi.    #
    # res_df["ma30_1m"] = res_df['close'].rolling(30).mean()
    # res_df["ma60_1m"] = res_df['close'].rolling(60).mean()
    # res_df = dtk_plot(res_df, dtk_itv2='15m', hhtf_entry=15, use_dtk_line=config.loc_set.zone.use_dtk_line)

    return res_df


def short_ep_loc(res_df, config, i, np_timeidx, show_detail=True):

    strat_version = config.strat_version

    # ------- param init ------- #
    open_side = None

    mr_const_cnt = 0
    mr_score = 0
    zone = 'n'

    if config.ep_set.entry_type == 'MARKET':
        if config.tp_set.tp_type != 'MARKET':
            tp_fee = config.trader_set.market_fee + config.trader_set.limit_fee
        else:
            tp_fee = config.trader_set.market_fee + config.trader_set.market_fee
        out_fee = config.trader_set.market_fee + config.trader_set.market_fee
    else:
        if config.tp_set.tp_type != 'MARKET':
            tp_fee = config.trader_set.limit_fee + config.trader_set.limit_fee
        else:
            tp_fee = config.trader_set.limit_fee + config.trader_set.market_fee
        out_fee = config.trader_set.limit_fee + config.trader_set.market_fee


    # -------------- candle_ratio -------------- #
    # if config.loc_set.zone.c_itv_ticks != "None":
    if config.loc_set.point.candle_ratio != "None":

      # -------------- candle_ratio_v0 (1m initial tick 기준임)  -------------- #
      if strat_version in ['v5_2']:
        mr_const_cnt += 1
        candle_ratio_ = res_df['candle_ratio'].iloc[i]
        # body_ratio_ = res_df['body_ratio'].iloc[i]
        if candle_ratio_ >= config.loc_set.point.candle_ratio:
          mr_score += 1

        if show_detail:
          sys_log3.warning("candle_ratio_ : {}".format(candle_ratio_))

      # -------------- candle_ratio_v1 (previous)  -------------- #
      if strat_version in ['v7_3']:
        mr_const_cnt += 1
        prev_hclose_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)
        h_candle_ratio_ = res_df['h_candle_ratio'].iloc[prev_hclose_idx]
        h_body_ratio_ = res_df['h_body_ratio'].iloc[prev_hclose_idx]
        if h_candle_ratio_ + h_body_ratio_/100 <= -config.loc_set.point.candle_ratio:
            mr_score += 1

        if show_detail:
            sys_log3.warning("h_candle_ratio_ : {}".format(h_candle_ratio_))

    if config.loc_set.point.candle_ratio2 != "None":

        #     candle_ratio_v2 (current)     #
      mr_const_cnt += 1
      prev_hclose_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)
      hc_res_df = res_df.iloc[prev_hclose_idx + 1:i + 1].copy()
      ho = hc_res_df['open'].iloc[0]
      hh = hc_res_df['high'].max()
      hl = hc_res_df['low'].min()
      hc = hc_res_df['close'].iloc[-1]
      # score = candle_score(ho, hh, hl, hc, updown='down', unsigned=False)
      score, _ = candle_score(ho, hh, hl, ho, updown=None, unsigned=False)
      if score <= -config.loc_set.point.candle_ratio2:
        mr_score += 1

      if show_detail:
        sys_log3.warning("candle_ratio_v2 : {}".format(score))
    
    # # -------------- tr scheduling -------------- #
    # if config.loc_set.zone.tr_thresh != "None":

    #   mr_const_cnt += 1
    #   tr = ((done_tp - ep_list[0] - tp_fee * ep_list[0]) / (ep_list[0] - done_out + out_fee * ep_list[0]))

    # -------------- spread scheduling -------------- #
    if config.loc_set.zone.short_spread != "None":

        mr_const_cnt += 1

        spread = (res_df['bb_base_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] - tp_fee * res_df['bb_base_5m'].iloc[
            # spread = (res_df['bb_base_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] - out_fee * res_df['bb_base_5m'].iloc[
            # i]) / (res_df['bb_base_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] + tp_fee *
            i]) / (res_df['bb_base_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] + out_fee *
                  res_df['bb_base_5m'].iloc[i])
        # spread = (res_df['bb_base_15m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] - tp_fee * res_df['bb_base_15m'].iloc[
        #     i]) / (res_df['bb_base_15m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] + out_fee *
        #             res_df['bb_base_15m'].iloc[i])

        # spread = (res_df['dc_upper_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] - tp_fee * res_df['bb_lower_5m'].iloc[
        #     i]) / (res_df['dc_upper_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] + out_fee *
        #             res_df['bb_lower_5m'].iloc[i])
        # spread = (res_df['short_rtc_gap'].iloc[i] * (0.443) - tp_fee * res_df['short_ep'].iloc[
        #     i]) / (res_df['short_rtc_gap'].iloc[i] * (0.417) + out_fee * res_df['short_ep'].iloc[i])

        # spread = (res_df['dc_upper_15m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] - tp_fee * res_df['dc_lower_5m'].iloc[
        #     i]) / (res_df['dc_upper_15m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] + out_fee *
        #             res_df['dc_lower_5m'].iloc[i])
        # spread = ((res_df['dc_upper_15m'].iloc[i] - res_df['dc_lower_5m'].iloc[i])/2 - tp_fee * res_df['dc_lower_5m'].iloc[
        #     i]) / ((res_df['dc_upper_15m'].iloc[i] - res_df['dc_lower_5m'].iloc[i])/2 + out_fee *
        #             res_df['dc_lower_5m'].iloc[i])

        if spread >= config.loc_set.zone.short_spread:
            mr_score += 1

        if show_detail:
            sys_log3.warning("spread : {}".format(spread))

    # -------------- dtk -------------- #
    if config.loc_set.zone.dt_k != "None":

        mr_const_cnt += 1
        # if res_df['dc_lower_%s' % config.loc_set.zone.dtk_dc_itv].iloc[i] >= res_df['short_rtc_1'].iloc[i] - res_df['h_short_rtc_gap'].iloc[i] * config.loc_set.zone.dt_k:
        #     dtk_v1 & v2 platform     #
        if config.loc_set.zone.dtk_dc_itv != "None":
            dc = res_df['dc_lower_%s' % config.loc_set.zone.dtk_dc_itv].iloc[i]
            dt_k = res_df['short_dtk_1_{}'.format(strat_version)].iloc[i] - \
                  res_df['short_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k
            if dc >= dt_k:
                mr_score += 1

                #     dc_v2   #
        else:
            dc = res_df['dc_lower_v2_{}'.format(strat_version)].iloc[i]
            dt_k = res_df['short_dtk_1_{}'.format(strat_version)].iloc[i] - \
                  res_df['short_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k
            if dc >= dt_k:
                # if res_df['dc_lower_v2_{}'.format(strat_version)].iloc[i] >= res_df['short_dtk_1_{}'.format(strat_version)].iloc[i] - res_df['short_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k and \
                # res_df['dc_upper_v2_{}'.format(strat_version)].iloc[i] <= res_df['long_dtk_1_{}'.format(strat_version)].iloc[i] + res_df['long_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k:
                mr_score += 1

        if show_detail:
            sys_log3.warning("dc : {}".format(dc))
            sys_log3.warning("dt_k : {}".format(dt_k))
            
      # -------------- candle_dt_k -------------- #
    # mr_const_cnt += 1
    # # if res_df['dc_lower_1m'].iloc[i] >= res_df['hclose_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    # if res_df['dc_lower_1m'].iloc[i] >= res_df['hlow_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    #   mr_score += 1        

    # mr_const_cnt += 1
    # if res_df['dc_upper_1m'].iloc[i] <= res_df['hhigh_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    # # if res_df['dc_upper_1m'].iloc[i] <= res_df['hopen_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    #   mr_score += 1  


    # -------------- zone rejection  -------------- #
    if config.loc_set.zone.zone_rejection:

        #       config 로 통제할 수 없는 rejection 은 strat_version 으로 조건문을 나눔 (lvrg_set 과 동일)

        # --------- by bb --------- # 

          #     bb & close   #
        if strat_version in ["v5_2"]:
          mr_const_cnt += 1
          # if res_df['close'].iloc[i] < res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:   # org
          # if res_df['close'].iloc[i] > res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:  # inv
          # if res_df['close'].iloc[i] > res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          if res_df['close'].iloc[i] > res_df['bb_upper2_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          # if res_df['close'].iloc[i] > res_df['bb_upper3_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
              mr_score += 1

              if show_detail:
                sys_log3.warning("bb & close passed")

          #     bb & bb   #           
        if strat_version in ["v7_3"]:

          mr_const_cnt += 1
          if res_df['bb_upper_5m'].iloc[i] < res_df['bb_base_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          # if res_df['bb_upper_1m'].iloc[i] < res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
            mr_score += 1

            if show_detail:
                sys_log3.warning("bb & bb passed")

            #     bb & ep   #
          mr_const_cnt += 1
          # if res_df['short_ep_{}'.format(strat_version)].iloc[i] < res_df['bb_base_15m'].iloc[i]:
          # if res_df['short_ep_{}'.format(strat_version)].iloc[i] < res_df['bb_base_15m'].iloc[i] + res_df['bb_gap_15m'].iloc[i]:
          # if res_df['short_ep_{}'.format(strat_version)].iloc[i] < res_df['bb_base_5m'].iloc[i]:
          if res_df['short_ep_{}'.format(strat_version)].iloc[i] < res_df['bb_upper_5m'].iloc[i]:
              mr_score += 1

              if show_detail:
                sys_log3.warning("bb & ep passed")

            #     bb & dc   #
          mr_const_cnt += 1
          # if res_df['bb_base_%s' % config.loc_set.zone.bbz_itv].iloc[i] <= res_df['dc_upper_1m'].iloc[i] <= res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          
          prev_hopen_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1 + config.loc_set.zone.c_itv_ticks) + config.loc_set.zone.ad_idx
          # if res_df['dc_upper_5m'].iloc[prev_hopen_idx] < res_df['bb_upper_15m'].iloc[i]:
          if res_df['dc_upper_5m'].iloc[prev_hopen_idx] < res_df['bb_upper_15m'].iloc[prev_hopen_idx]:
            mr_score += 1

            if show_detail:
                sys_log3.warning("bb & dc passed")

          # --------- by ema --------- # 

          #    bb & ema   #
        if strat_version in ["v7_3"]:
          mr_const_cnt += 1
          # if res_df['bb_upper_15m'].iloc[i] < res_df['ema_5m'].iloc[i]:
          if res_df['dc_upper_5m'].iloc[i] < res_df['ema_5m'].iloc[i]:
            mr_score += 1

            if show_detail:
                sys_log3.warning("bb & ema passed")

          #    close & ema   #
        if strat_version in ["v5_2"]:
          mr_const_cnt += 1
          # if res_df['short_ep'].iloc[i] < res_df['ema_5m'].iloc[i]:
          if res_df['close'].iloc[i] < res_df['ema_5m'].iloc[i]:
              mr_score += 1

              if show_detail:
                sys_log3.warning("close & ema passed")


        # --------- by dc --------- # 
        
          #     descending dc    #
        # mr_const_cnt += 1
        # if res_df['dc_lower_5m'].iloc[i] <= res_df['dc_lower_5m'].iloc[i - 50 : i].min():
        #   mr_score += 1

        # --------- by candle --------- #
        # mr_const_cnt += 1
        # if res_df['short_ep_{}'.format(strat_version)].iloc[i] <= res_df['hclose_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
        #     mr_score += 1

        # --------- by macd --------- #
        # mr_const_cnt += 1
        # if res_df['ma30_1m'].iloc[i] < res_df['ma60_1m'].iloc[i]:
        #     mr_score += 1


        # --------- by zone_dtk --------- #
        # mr_const_cnt += 1
        # if res_df['zone_dc_upper_v2_{}'.format(strat_version)].iloc[i] < res_df['long_dtk_plot_1'].iloc[i] + res_df['long_dtk_plot_gap'].iloc[
        #     i] * config.loc_set.zone.zone_dt_k:
        #   mr_score += 1

    # -------------- zoned tr_set - post_Work -------------- #
    if config.tr_set.c_ep_gap != "None":

        #       by bb       # 
        # if res_df['close'].iloc[i] > res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:

        #       by zone_dtk       #

        #         c_zone        #
        if res_df['zone_dc_upper_v2_{}'.format(strat_version)].iloc[i] > res_df['long_dtk_plot_1'].iloc[i] + \
                res_df['long_dtk_plot_gap'].iloc[
                    i] * config.loc_set.zone.zone_dt_k:

            if config.ep_set.static_ep:
                res_df['short_ep_{}'.format(strat_version)].iloc[i] = res_df['short_ep2_{}'.format(strat_version)].iloc[
                    i]
            else:
                res_df['short_ep_{}'.format(strat_version)] = res_df['short_ep2_{}'.format(strat_version)]

            if config.out_set.static_out:
                res_df['short_out_{}'.format(strat_version)].iloc[i] = \
                res_df['short_out_org_{}'.format(strat_version)].iloc[i]
            else:
                res_df['short_out_{}'.format(strat_version)] = res_df['short_out_org_{}'.format(strat_version)]

            zone = 'c'

        #         t_zone        #
        else:

            # mr_const_cnt += 1   # zone_rejection - temporary

            if config.ep_set.static_ep:
                res_df['short_ep_{}'.format(strat_version)].iloc[i] = \
                res_df['short_ep_org_{}'.format(strat_version)].iloc[i]
            else:
                res_df['short_ep_{}'.format(strat_version)] = res_df['short_ep_org_{}'.format(strat_version)]

            if config.out_set.static_out:
                res_df['short_out_{}'.format(strat_version)].iloc[i] = \
                res_df['short_out2_{}'.format(strat_version)].iloc[i]
            else:
                res_df['short_out_{}'.format(strat_version)] = res_df['short_out2_{}'.format(strat_version)]

            zone = 't'

    if mr_const_cnt == mr_score:
        open_side = OrderSide.SELL

    return res_df, open_side, zone


def long_ep_loc(res_df, config, i, np_timeidx, show_detail=True):

    strat_version = config.strat_version

    # ------- param init ------- #
    open_side = None

    mr_const_cnt = 0
    mr_score = 0
    zone = 'n'

    if config.ep_set.entry_type == 'MARKET':
        if config.tp_set.tp_type != 'MARKET':
            tp_fee = config.trader_set.market_fee + config.trader_set.limit_fee
        else:
            tp_fee = config.trader_set.market_fee + config.trader_set.market_fee
        out_fee = config.trader_set.market_fee + config.trader_set.market_fee
    else:
        if config.tp_set.tp_type != 'MARKET':
            tp_fee = config.trader_set.limit_fee + config.trader_set.limit_fee
        else:
            tp_fee = config.trader_set.limit_fee + config.trader_set.market_fee
        out_fee = config.trader_set.limit_fee + config.trader_set.market_fee


    # -------------- candle_ratio -------------- #
    # if config.loc_set.zone.c_itv_ticks != "None":
    if config.loc_set.point.candle_ratio != "None":

      # -------------- candle_ratio_v0 (1m initial tick 기준임)  -------------- #
      if strat_version in ['v5_2']:
        mr_const_cnt += 1
        candle_ratio_ = res_df['candle_ratio'].iloc[i]
        # body_ratio_ = res_df['body_ratio'].iloc[i]
        if candle_ratio_ >= config.loc_set.point.candle_ratio:
          mr_score += 1

        if show_detail:
            sys_log3.warning("candle_ratio_ : {}".format(candle_ratio_))

      # -------------- candle_ratio_v1 (previous)  -------------- #
      if strat_version in ['v7_3']:
        mr_const_cnt += 1
        prev_hclose_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)
        h_candle_ratio_ = res_df['h_candle_ratio'].iloc[prev_hclose_idx]
        h_body_ratio_ = res_df['h_body_ratio'].iloc[prev_hclose_idx]
        if h_candle_ratio_ + h_body_ratio_/100 >= config.loc_set.point.candle_ratio:
            mr_score += 1

        if show_detail:
            sys_log3.warning("h_candle_ratio_ : {}".format(h_candle_ratio_))

    if config.loc_set.point.candle_ratio2 != "None":

      #     candle_ratio_v2 (current)     #
      mr_const_cnt += 1
      prev_hclose_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)
      hc_res_df = res_df.iloc[prev_hclose_idx + 1:i + 1].copy()
      ho = hc_res_df['open'].iloc[0]
      hc = hc_res_df['close'].iloc[-1]
      hh = hc_res_df['high'].max()
      hl = hc_res_df['low'].min()
      # score = candle_score(ho, hh, hl, hc, updown='up', unsigned=False)
      score, _ = candle_score(ho, hh, hl, ho, updown=None, unsigned=False)
      if score >= config.loc_set.point.candle_ratio2:
        mr_score += 1

        if show_detail:
            sys_log3.warning("candle_ratio_v2 : {}".format(score))

    # -------------- spread scheduling -------------- #
    if config.loc_set.zone.long_spread != "None":

        mr_const_cnt += 1

        # spread = (res_df['bb_upper_5m'].iloc[i] - res_df['bb_base_5m'].iloc[i] - tp_fee * res_df['bb_base_5m'].iloc[
        #     i]) / (res_df['bb_base_5m'].iloc[i] - res_df['bb_lower_5m'].iloc[i] + out_fee *
        #             res_df['bb_base_5m'].iloc[i])
        # spread = (res_df['bb_upper_5m'].iloc[i] - res_df['bb_base_15m'].iloc[i] - tp_fee * res_df['bb_base_15m'].iloc[
        #     i]) / (res_df['bb_upper_5m'].iloc[i] - res_df['bb_base_15m'].iloc[i] + out_fee *
        #             res_df['bb_base_15m'].iloc[i])

        spread = (res_df['bb_upper_5m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] - tp_fee * res_df['bb_upper_5m'].iloc[
            # spread = (res_df['bb_upper_5m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] - out_fee * res_df['bb_upper_5m'].iloc[
            # i]) / (res_df['bb_upper_5m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] + tp_fee *
            i]) / (res_df['bb_upper_5m'].iloc[i] - res_df['dc_lower_5m'].iloc[i] + out_fee *
                  res_df['bb_upper_5m'].iloc[i])
        # spread = (res_df['long_rtc_gap'].iloc[i] * (0.443) - tp_fee * res_df['long_ep'].iloc[
        #     i]) / (res_df['long_rtc_gap'].iloc[i] * (0.417) + out_fee * res_df['long_ep'].iloc[i])

        # spread = (res_df['dc_upper_5m'].iloc[i] - res_df['dc_lower_15m'].iloc[i] - tp_fee * res_df['dc_upper_5m'].iloc[
        #     i]) / (res_df['dc_upper_5m'].iloc[i] - res_df['dc_lower_15m'].iloc[i] + out_fee *
        #             res_df['dc_upper_5m'].iloc[i])
        # spread = ((res_df['dc_upper_5m'].iloc[i] - res_df['dc_lower_15m'].iloc[i])/2 - tp_fee * res_df['dc_upper_5m'].iloc[
        #     i]) / ((res_df['dc_upper_5m'].iloc[i] - res_df['dc_lower_15m'].iloc[i])/2 + out_fee *
        #             res_df['dc_upper_5m'].iloc[i])

        if spread >= config.loc_set.zone.long_spread:
            mr_score += 1

        if show_detail:
            sys_log3.warning("spread : {}".format(spread))

    # -------------- dtk -------------- #
    if config.loc_set.zone.dt_k != "None":

        mr_const_cnt += 1
        # if res_df['dc_upper_%s' % config.loc_set.zone.dtk_dc_itv].iloc[i] <= res_df['long_rtc_1'].iloc[i] + res_df['long_rtc_gap'].iloc[i] * config.loc_set.zone.dt_k:
        #     dtk_v1 & v2 platform    #
        if config.loc_set.zone.dtk_dc_itv != "None":
            dc = res_df['dc_upper_%s' % config.loc_set.zone.dtk_dc_itv].iloc[i]
            dt_k = res_df['long_dtk_1_{}'.format(strat_version)].iloc[i] + \
                  res_df['long_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k
            if dc <= dt_k:
                mr_score += 1

        else:
            #     dc_v2     #
            dc = res_df['dc_upper_v2_{}'.format(strat_version)].iloc[i]
            dt_k = res_df['long_dtk_1_{}'.format(strat_version)].iloc[i] + \
                  res_df['long_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k
            if dc <= dt_k:
                # if res_df['dc_upper_v2_{}'.format(strat_version)].iloc[i] >= res_df['long_dtk_1_{}'.format(strat_version)].iloc[i] + res_df['long_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k:

                # if res_df['dc_upper_v2_{}'.format(strat_version)].iloc[i] <= res_df['long_dtk_1_{}'.format(strat_version)].iloc[i] + res_df['long_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k and \
                #   res_df['dc_lower_v2_{}'.format(strat_version)].iloc[i] >= res_df['short_dtk_1_{}'.format(strat_version)].iloc[i] - res_df['short_dtk_gap_{}'.format(strat_version)].iloc[i] * config.loc_set.zone.dt_k:

                mr_score += 1

        if show_detail:
            sys_log3.warning("dc : {}".format(dc))
            sys_log3.warning("dt_k : {}".format(dt_k))

      # -------------- candle_dt_k -------------- #
    # mr_const_cnt += 1
    # # if res_df['dc_upper_1m'].iloc[i] <= res_df['hclose_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    # if res_df['dc_upper_1m'].iloc[i] <= res_df['hhigh_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    #   mr_score += 1  

    # mr_const_cnt += 1
    # if res_df['dc_lower_1m'].iloc[i] >= res_df['hlow_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    # # if res_df['dc_lower_1m'].iloc[i] >= res_df['hopen_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
    #   mr_score += 1  

    # -------------- zone rejection  -------------- #
    if config.loc_set.zone.zone_rejection:

        # --------- by bb --------- #    
        
          #     bb & close   #
        if strat_version in ["v5_2"]:

          mr_const_cnt += 1
          # if res_df['close'].iloc[i] > res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:    # org
          # if res_df['close'].iloc[i] < res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:  # inv
          # if res_df['close'].iloc[i] < res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          if res_df['close'].iloc[i] < res_df['bb_lower2_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          # if res_df['close'].iloc[i] < res_df['bb_lower3_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
              mr_score += 1

              if show_detail:
                  sys_log3.warning("bb & close passed")

          #     bb & bb   #
        if strat_version in ["v7_3"]:

          mr_const_cnt += 1
          if  res_df['bb_lower_5m'].iloc[i] > res_df['bb_base_%s' % config.loc_set.zone.bbz_itv].iloc[i]:
          # if res_df['bb_lower_1m'].iloc[i] > res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:            
              mr_score += 1

              if show_detail:
                  sys_log3.warning("bb & bb passed")

            #     bb & ep   #
          mr_const_cnt += 1
          # if res_df['long_ep_{}'.format(strat_version)].iloc[i] > res_df['bb_base_15m'].iloc[i]:
          # if res_df['long_ep_{}'.format(strat_version)].iloc[i] > res_df['bb_base_15m'].iloc[i] + res_df['bb_gap_15m'].iloc[i]:
          # if res_df['long_ep_{}'.format(strat_version)].iloc[i] > res_df['bb_base_5m'].iloc[i]:
          if res_df['long_ep_{}'.format(strat_version)].iloc[i] > res_df['bb_lower_5m'].iloc[i]:
              mr_score += 1

              if show_detail:
                  sys_log3.warning("bb & ep passed")
          
            #     bb & dc   #
          mr_const_cnt += 1
          # if res_df['bb_base_%s' % config.loc_set.zone.bbz_itv].iloc[i] >= res_df['dc_lower_1m'].iloc[i] >= res_df['bb_lower_%s' % config.loc_set.zone.bbz_itv].iloc[i]:

          prev_hopen_idx = i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1 + config.loc_set.zone.c_itv_ticks) + config.loc_set.zone.ad_idx
          # if res_df['dc_lower_5m'].iloc[prev_hopen_idx] > res_df['bb_lower_15m'].iloc[i]:
          if res_df['dc_lower_5m'].iloc[prev_hopen_idx] > res_df['bb_lower_15m'].iloc[prev_hopen_idx]:
            mr_score += 1

            if show_detail:
                sys_log3.warning("bb & dc passed")

        # --------- by ema --------- # 

          #     bb & ema   #
        if strat_version in ["v7_3"]:

          mr_const_cnt += 1
          # if res_df['bb_lower_15m'].iloc[i] > res_df['ema_5m'].iloc[i]:
          if res_df['dc_lower_5m'].iloc[i] > res_df['ema_5m'].iloc[i]:
            mr_score += 1

            if show_detail:
              sys_log3.warning("bb & ema passed")

          #     close & ema     #
        if strat_version in ["v5_2"]:

          mr_const_cnt += 1
          # if  res_df['long_ep'].iloc[i] > res_df['ema_5m'].iloc[i]:
          if res_df['close'].iloc[i] > res_df['ema_5m'].iloc[i]:
              mr_score += 1

              if show_detail:
                sys_log3.warning("close & ema passed")
        
          
        # --------- by dc --------- # 

          #     ascending dc    #
        # mr_const_cnt += 1
        # if res_df['dc_upper_5m'].iloc[i] >= res_df['dc_upper_5m'].iloc[i - 50 : i].max():
        #   mr_score += 1
          
        # --------- by candle --------- #
        # mr_const_cnt += 1
        # if res_df['long_ep_{}'.format(strat_version)].iloc[i] >= res_df['hclose_60'].iloc[i - (np_timeidx[i] % config.loc_set.zone.c_itv_ticks + 1)]:
        #     mr_score += 1
        
        # --------- by macd --------- #
        # mr_const_cnt += 1
        # if res_df['ma30_1m'].iloc[i] > res_df['ma60_1m'].iloc[i]:
        #     mr_score += 1

        # --------- by zone_dtk --------- #
        # mr_const_cnt += 1
        # if res_df['zone_dc_lower_v2_{}'.format(strat_version)].iloc[i] > res_df['short_dtk_plot_1'].iloc[i] - res_df['short_dtk_plot_gap'].iloc[i] * config.loc_set.zone.zone_dt_k:
        #   mr_score += 1

    # -------------- zoned tr_set - post_work -------------- #
    if config.tr_set.c_ep_gap != "None":
        #       by bb       # 
        # if res_df['close'].iloc[i] < res_df['bb_upper_%s' % config.loc_set.zone.bbz_itv].iloc[i]:

        #       by zone_dtk       #

        #         c_zone        #
        if res_df['zone_dc_lower_v2_{}'.format(strat_version)].iloc[i] < res_df['short_dtk_plot_1'].iloc[i] - \
                res_df['short_dtk_plot_gap'].iloc[i] * config.loc_set.zone.zone_dt_k:

            if config.ep_set.static_ep:
                res_df['long_ep_{}'.format(strat_version)].iloc[i] = res_df['long_ep2_{}'.format(strat_version)].iloc[i]
            else:
                res_df['long_ep_{}'.format(strat_version)] = res_df['long_ep2_{}'.format(strat_version)]

            if config.out_set.static_out:
                res_df['long_out_{}'.format(strat_version)].iloc[i] = \
                res_df['long_out_org_{}'.format(strat_version)].iloc[i]
            else:
                res_df['long_out_{}'.format(strat_version)] = res_df['long_out_org_{}'.format(strat_version)]

            zone = 'c'

            # mr_const_cnt += 1
            # dc_lb_period = 100
            # if np.sum((res_df['dc_upper_15m'] > res_df['dc_upper_15m'].shift(15)).iloc[i - dc_lb_period:i]) == 0:
            #   mr_score += 1

            #         t_zone        #
        else:

            # mr_const_cnt += 1   # zone_rejection - temporary

            if config.ep_set.static_ep:
                res_df['long_ep_{}'.format(strat_version)].iloc[i] = \
                res_df['long_ep_org_{}'.format(strat_version)].iloc[i]
            else:
                res_df['long_ep_{}'.format(strat_version)] = res_df['long_ep_org_{}'.format(strat_version)]

            if config.out_set.static_out:
                res_df['long_out_{}'.format(strat_version)].iloc[i] = res_df['long_out2_{}'.format(strat_version)].iloc[
                    i]
            else:
                res_df['long_out_{}'.format(strat_version)] = res_df['long_out2_{}'.format(strat_version)]

            zone = 't'

    if mr_const_cnt == mr_score:
        open_side = OrderSide.BUY

    return res_df, open_side, zone
