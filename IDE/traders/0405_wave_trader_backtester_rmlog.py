import os

#        1. relative path should be static '/IDE' 를 가리켜야함, 기준은 script 실행 dir 기준 (bots, back_idep)
#        2. 깊이가 다르면, './../' 이런식의 표현으로는 동일 pkg_path 에 접근할 수 없음
# print(os.getcwd())
# pkg_path = os.path.abspath('./../')
pkg_path = r"C:\Users\Lenovo\PycharmProjects\System_Trading\JnQ\IDE"  # system env. 에 따라 가변적
os.chdir(pkg_path)

from funcs_binance.binance_futures_modules import *  # math, pandas, bot_config (API_key & clients)
from funcs_binance.funcs_trader_modules import get_streamer, read_write_cfg_list, get_income_info_v2, calc_ideal_profit_v4, \
    get_new_df, check_hl_out, check_signal_out, check_limit_tp_exec, log_sub_tp_exec, get_dynamic_tpout, check_breakout_qty, check_ei_k_v2, get_balance, \
    get_tpepout, check_ei_k_onbarclose_v2, init_set, get_open_side_v2, get_p_tpqty
from funcs_binance.funcs_order_logger_hedge import limit_order, partial_limit_order_v4, cancel_order_list, market_close_order_v2
from funcs.funcs_trader import intmin_np
import numpy as np  # for np.nan
import time
import pickle
import logging.config
from pathlib import Path
from easydict import EasyDict
from datetime import datetime
import shutil


class Trader:
    def __init__(self, utils_public, utils_list, config_name_list):
        # ------ ID info. ------ #
        self.utils_public = utils_public
        self.utils_list = utils_list
        self.config_name_list = config_name_list
        self.config_list = None
        self.config = None
        self.utils = None

        # ------ balance ------ #
        self.available_balance = None
        self.over_balance = None
        self.min_balance = 5.0  # USDT

        # ------ pnl ------ #
        self.income = 0.0
        self.accumulated_income = 0.0
        self.accumulated_profit = 1.0
        self.ideal_accumulated_profit = 1.0

        # ------ obj ------ #
        self.sub_client = None
        self.streamer = None

    def run(self):
        exec_file_name = Path(__file__).stem

        # ------ path definition ------ #
        log_path_list = ["sys_log", "trade_log", "df_log"]
        sys_log_path, trade_log_path, df_log_path = [os.path.join(pkg_path, path_, exec_file_name) for path_ in log_path_list]

        for path_ in [sys_log_path, trade_log_path, df_log_path]:
            os.makedirs(path_, exist_ok=True)

        cfg_path_list = [os.path.join(pkg_path, "config", name_) for name_ in self.config_name_list]

        initial_set = 1
        while 1:
            # ------ load config (refreshed by every trade) ------ #
            self.config_list = read_write_cfg_list(cfg_path_list)
            #       self.config = config1 & equal config.trader_set      #
            for cfg_idx, cfg_ in enumerate(self.config_list):
                if cfg_idx != 0:
                    cfg_.trader_set = self.config.trader_set
                else:
                    self.config = cfg_

            # ------ check symbol_changed ------ #
            if self.config.trader_set.symbol_changed:
                self.config_list[0].trader_set.symbol_changed = 0
                initial_set = 1  # symbol changed -> reset initial_set

            if initial_set:
                # ------ check backtrade ------ #
                if self.config.trader_set.backtrade:    # initial_set 내부에 놓았지만, backtrade 시에는 한번만 진행될거
                    self.streamer = get_streamer(self)

                # ------ rewrite modified self.config_list ------ #
                read_write_cfg_list(cfg_path_list, mode='w', edited_cfg_list=self.config_list)

                # ------ trade_log_fullpath define ------ #
                # trade_log = {}  # for ideal ep & tp logging
                # trade_log_fullpath = os.path.join(trade_log_path, trade_log_name)
                trade_log_name = "{}_{}.pkl".format(self.config.trader_set.symbol, str(datetime.now().timestamp()).split(".")[0])

                # ------ copy base_cfg.json -> {ticker}.json (log_cfg name) ------ #
                src_cfg_path = sys_log_path.replace(exec_file_name, "base_cfg.json")  # dir 대신 .json 가져옴
                dst_cfg_path = os.path.join(sys_log_path, trade_log_name.replace(".pkl", ".json"))
                # print("dst_cfg_path :", dst_cfg_path)
                # quit()

                try:
                    shutil.copy(src_cfg_path, dst_cfg_path)
                except Exception as e:
                    print("error in shutil.copy() :", e)
                    continue

            # ------ set logger info. to {ticker}.json - offer realtime modification ------ #
            try:
                with open(dst_cfg_path, 'r') as sys_cfg:  # trade end 시에도 반영하기 위함 - 윗 phase 와 분리 이유
                    sys_log_cfg = EasyDict(json.load(sys_cfg))

                if initial_set:  # dump edited_cfg - sys_log_cfg 정의가 필요해서 윗 phase 와 분리됨
                    sys_log_cfg.handlers.file_rot.filename = \
                        os.path.join(sys_log_path, trade_log_name.replace(".pkl", ".log"))  # log_file name - trade_log_name 에 종속
                    logging.getLogger("apscheduler.executors.default").propagate = False

                    with open(dst_cfg_path, 'w') as edited_cfg:
                        json.dump(sys_log_cfg, edited_cfg, indent=3)

                    logging.config.dictConfig(sys_log_cfg)
                    sys_log = logging.getLogger()
                    sys_log.info('# ----------- {} ----------- #'.format(exec_file_name))
                    sys_log.info("pkg_path : {}".format(pkg_path))

                    limit_leverage, self.sub_client = init_set(self)  # self.config 가 위에서 정의된 상황
                    sys_log.info("initial_set done\n")
                    initial_set = 0

            except Exception as e:
                print("error in load sys_log_cfg :", e)
                time.sleep(self.config.trader_set.api_retry_term)
                continue

            # ------ check run ------ #
            if not self.config.trader_set.run:
                time.sleep(self.config.trader_set.realtime_term)  # give enough time to read config
                continue

            # ------ open param. init by every_trades ------ #
            load_new_df = 1
            self.utils = None
            open_side, pos_side = None, None
            ep_loc_point2 = 0   # use_point2 사용시 loop 내에서 enlist once 를 위한 var.
            ep_out = 0

            while 1:
                if load_new_df:
                    # ------ log last trading time ------ #
                    #        미체결을 고려해, load_new_df 마다 log 수행       #
                    # trade_log["last_trading_time"] = str(datetime.now())
                    # with open(trade_log_fullpath, "wb") as dict_f:
                    #     pickle.dump(trade_log, dict_f)

                    # ------------ get_new_df ------------ #
                    start_ts = time.time()
                    if self.config.trader_set.backtrade:
                        res_df = next(self.streamer)    # Todo, 무결성 검증 미진행
                        load_new_df = 0
                    else:
                        res_df, _, load_new_df = get_new_df(self)
                    sys_log.info("~ load_new_df time : %.2f" % (time.time() - start_ts))

                    # ------------ self.utils_ ------------ #
                    try:
                        res_df = self.utils_public.sync_check(res_df, self.config)  # function usage format maintenance
                        sys_log.info('~ sync_check time : %.5f' % (time.time() - start_ts))
                        np_timeidx = np.array([intmin_np(date_) for date_ in res_df.index.to_numpy()])
                        res_df = self.utils_public.public_indi(res_df, self.config, np_timeidx)
                        sys_log.info('~ public_indi time : %.5f' % (time.time() - start_ts))

                        #        use_point2 사용시, 해당 ID 로만 enlist_ 진행        #
                        if ep_loc_point2:
                            res_df = self.utils.enlist_rtc(res_df, self.config, np_timeidx)
                            res_df = self.utils.enlist_tr(res_df, self.config, np_timeidx)
                        else:
                            for utils_, config_ in zip(self.utils_list, self.config_list):
                                res_df = utils_.enlist_rtc(res_df, config_, np_timeidx)
                                res_df = utils_.enlist_tr(res_df, config_, np_timeidx)
                        sys_log.info('~ enlist_rtc & enlist_tr time : %.5f' % (time.time() - start_ts))
                        sys_log.info('res_df.index[-1] : {}'.format(res_df.index[-1]))

                    except Exception as e:
                        sys_log.error("error in self.utils_ : {}".format(e))
                        load_new_df = 1
                        continue

                    # ---------------- ep_loc - get_open_side_v2 ---------------- #
                    if open_side is None:  # open_signal not exists, check ep_loc
                        try:
                            if self.config.trader_set.df_log:  # save res_df at ep_loc
                                excel_name = str(datetime.now()).replace(":", "").split(".")[0]
                                res_df.reset_index().to_feather(df_log_path + "/%s.ftr" % excel_name, compression='lz4')

                            open_side, self.utils, self.config = get_open_side_v2(self, res_df, np_timeidx)

                        except Exception as e:
                            sys_log.error("error in ep_loc phase : {}".format(e))
                            continue

                        if open_side is not None:  # res_df_open 정의는 이곳에서 해야함 - 아래서 할 경우 res_df_open 갱신되는 문제
                            res_df_open = res_df.copy()

                # ------------ after load_new_df - check open_signal again ------------ #
                # <-- 이줄에다가 else 로 아래 phase 옮길 수 없나 ? --> 안됨, ep_loc survey 진행후에도 아래 phase 는 실행되어야함
                if open_side is not None:
                    # ------ 1. check_entry_sec for market_entry ------ #
                    if self.config.ep_set.entry_type == "MARKET" and not self.config.trader_set.backtrade:
                        check_entry_sec = datetime.now().second
                        if check_entry_sec > self.config.trader_set.check_entry_sec:
                            open_side = None
                            sys_log.warning("check_entry_sec : {}".format(check_entry_sec))
                            continue  # ep_loc_check = False 라서 open_side None phase 로 감 -> 무슨 의미 ? 어쨌든 wait_zone 으로 회귀

                    # ------ 2. init fee ------ #
                    if self.config.ep_set.entry_type == "MARKET":
                        fee = self.config.trader_set.market_fee
                    else:
                        fee = self.config.trader_set.limit_fee

                    #        a. ep_loc.point2 - point1 과 동시성이 성립하지 않음, 가 위치할 곳      #
                    #           i. out 이 point 에 따라 변경되기 때문에 이곳이 적합한 것으로 판단     #
                    #        b. load_df phase loop 돌릴 것
                    #        c. continue 바로하면 안되고, 분마다 진행해야할 것 --> waiting_zone while loop 적용
                    #           i. 첫 point2 검사는 바로진행해도 될것
                    #           ii. ei_k check 이 realtime 으로 진행되어야한다는 점
                    #               i. => ei_k check by ID

                    # ------ 3. set strat_version ------ #
                    strat_version = self.config.strat_version

                    # ------ 4. point2 (+ ei_k) phase ------ #
                    if self.config.ep_set.point2.use_point2:
                        ep_loc_point2 = 1
                        sys_log.warning("strat_version use_point2 : {}{}".format(strat_version, self.config.ep_set.point2.use_point2))

                        #        a. tp_j, res_df_open 으로 고정
                        c_i = self.config.trader_set.complete_index
                        ep_out = check_ei_k_onbarclose_v2(self, res_df_open, res_df, c_i, c_i, open_side)   # e_j, tp_j
                        #        b. e_j 에 관한 고찰 필요함, backtest 에는 i + 1 부터 시작하니 +1 하는게 맞을 것으로 봄
                        #          -> Todo, 좀더 명확하게, dc_lower_1m.iloc[i - 1] 에 last_index 가 할당되는게 맞아서
                        allow_ep_in, _ = self.utils_public.ep_loc_point2_v2(res_df, self.config, c_i + 1, out_j=None, side=open_side)   # e_j
                        if allow_ep_in:
                            break
                    else:   # point2 미사용시 바로 order phase 로 break
                        break

                # -------------- open_side is None - no_signal holding zone -------------- #
                #        1. 추후 position change platform 으로 변경 가능
                #           a. first_iter 사용
                #        2. ep_loc.point2 를 위해 이 phase 를 잘 활용해야할 것      #
                while 1:
                    # ------- check bar_ends - latest df confirmation ------- #
                    if self.config.trader_set.backtrade or datetime.timestamp(res_df.index[-1]) < datetime.now().timestamp():
                        # ------ use_point2 == 1,  res_df 갱신 불필요
                        #        반대의 경우, utils 초기화 ------ #
                        if not ep_loc_point2:
                            self.utils = None

                        if not self.config.trader_set.backtrade:
                            sys_log.info('res_df[-1] timestamp : %s' % datetime.timestamp(res_df.index[-1]))
                            sys_log.info('current timestamp : %s' % datetime.now().timestamp() + "\n")

                            # ------- 1. get configure every bar_ends - trade_config ------- #
                            try:
                                self.config_list = read_write_cfg_list(cfg_path_list)
                            except Exception as e:
                                print("error in load config (waiting zone phase):", e)
                                time.sleep(1)
                                continue

                            # ------- 2. sys_log configuration ------- #
                            try:
                                with open(dst_cfg_path, 'r') as sys_cfg:
                                    sys_log_cfg = EasyDict(json.load(sys_cfg))
                                    logging.config.dictConfig(sys_log_cfg)
                                    sys_log = logging.getLogger()
                            except Exception as e:
                                print("error in load sys_log_cfg (waiting zone phase):", e)
                                time.sleep(self.config.trader_set.api_retry_term)
                                continue

                        load_new_df = 1
                        break  # return to load_new_df

                    else:
                        time.sleep(self.config.trader_set.realtime_term)  # <-- term for realtime market function
                        # time.sleep(self.config.trader_set.close_complete_term)   # <-- term for close completion

                if ep_out:  # 1m_bar close 까지 기다리는 logic
                    break

            if ep_out:  # ep_out init 을 위한 continue
                continue

            first_iter = True  # 포지션 변경하는 경우, 필요함
            while 1:  # <-- loop for 'check order type change condition'

                # ------ get tr_set x adj precision ------ #
                tp, ep, out, open_side = get_tpepout(self, open_side, res_df_open, res_df)
                # Todo, 실제로는 precision 조금 달라질 것, 큰 차이없다고 가정 (solved)
                price_precision, quantity_precision = get_precision(self.config.trader_set.symbol)
                tp, ep, out = [calc_with_precision(price_, price_precision) for price_ in [tp, ep, out]]  # includes half-dynamic tp

                # ------ set pos_side & open_price comparison ------ #
                open_price = res_df['open'].to_numpy()[-1]    # open 은 latest_index 의 open 사용
                if open_side == OrderSide.BUY:
                    pos_side = PositionSide.LONG
                    ep = min(open_price, ep)
                else:
                    pos_side = PositionSide.SHORT
                    ep = max(open_price, ep)

                leverage = self.utils_public.lvrg_set(res_df, self.config, open_side, ep, out, fee, limit_leverage)

                sys_log.info('tp : {}'.format(tp))
                sys_log.info('ep : {}'.format(ep))
                sys_log.info('out : {}'.format(out))
                sys_log.info('leverage : {}'.format(leverage))
                sys_log.info('~ tp ep out lvrg set time : %.5f' % (time.time() - start_ts))

                if not self.config.trader_set.backtrade:
                    while 1:
                        try:
                            request_client.change_initial_leverage(symbol=self.config.trader_set.symbol, leverage=leverage)
                        except Exception as e:
                            sys_log.error('error in change_initial_leverage : {}'.format(e))
                            time.sleep(self.config.trader_set.api_retry_term)
                            continue  # -->  ep market 인 경우에 조심해야함 - why ..?
                        else:
                            sys_log.info('leverage changed --> {}'.format(leverage))
                            break

                self.available_balance, self.over_balance, min_bal_bool = get_balance(self, first_iter, cfg_path_list)
                if min_bal_bool:
                    break
                sys_log.info('~ get balance time : %.5f' % (time.time() - start_ts))

                # ---------- calc. open_quantity ---------- #
                open_quantity = calc_with_precision(self.available_balance / ep * leverage, quantity_precision)
                sys_log.info("open_quantity : {}".format(open_quantity))

                # ---------- open order ---------- #
                orderside_changed = False
                if not self.config.trader_set.backtrade:
                    order_info = (self.available_balance, leverage)
                    post_order_res, self.over_balance, res_code = limit_order(self, self.config.ep_set.entry_type, open_side, pos_side,
                                                                              ep, open_quantity, order_info)
                    if res_code:  # order deny exception, res_code = 0
                        break

                # ------------ execution wait time ------------ #
                # Todo, iterator 객체에서 res_df 를 pop() 할 수 있게만 만들면 아래 형태 유지 가능함
                #  1. market 은 다음 bar 에 즉시 체결
                #  2. limit 은 hl_check 해야겠지
                # ------ 1. market : prevent close at open bar ------ #
                if self.config.ep_set.entry_type == OrderType.MARKET:
                    if self.config.trader_set.backtrade:
                        res_df = next(self.streamer)
                    else:
                        # enough time for open_quantity be consumed
                        while 1:
                            if datetime.now().timestamp() > datetime.timestamp(res_df.index[-1]):
                                break
                            else:
                                time.sleep(self.config.trader_set.realtime_term)  # <-- for realtime price function
                # ------ 2. limit : check ep_out (= ei_k & breakout_qty) ------ #
                else:
                    if self.config.trader_set.backtrade:
                        breakout = 0
                        while 1:
                            res_df = next(self.streamer)

                            c_i = self.config.trader_set.complete_index
                            if check_ei_k_onbarclose_v2(self, res_df_open, res_df, c_i, c_i, open_side):   # e_j, tp_j
                                break
                            # ------ entry ------ #
                            if open_side == OrderSide.BUY:
                                if res_df['low'].to_numpy()[c_i] <= ep:
                                    breakout = 1
                                    break
                            else:
                                if res_df['high'].to_numpy()[c_i] >= ep:
                                    breakout = 1
                                    break
                    else:
                        first_exec_qty_check = 1
                        check_time = time.time()
                        while 1:
                            if check_ei_k_v2(self, res_df_open, res_df, open_side):
                                break
                            first_exec_qty_check, check_time, breakout = check_breakout_qty(self, first_exec_qty_check,
                                                                                            check_time, post_order_res, open_quantity)
                            if breakout:
                                break

                # ------ when, open order time expired or executed ------ #
                #        regardless to position exist, cancel open orders       #
                # Todo, backtrader 에 불필요
                #  1. open_executedPrice_list, open_executedQty 정의 필요 (open_executedPrice_list = [ep]), real_pr unnecessary
                if not self.config.trader_set.backtrade:
                    open_executedPrice_list, open_executedQty = cancel_order_list(self.config.trader_set.symbol, [post_order_res],
                                                                                  self.config.ep_set.entry_type)
                else:
                    open_executedPrice_list = [ep]
                    open_executedQty = open_quantity if breakout else 0

                if orderside_changed:  # future_module
                    first_iter = False
                    sys_log.info('orderside_changed : {}\n'.format(orderside_changed))
                    continue
                else:
                    break

            # ------ reject unacceptable amount of asset ------ #
            if min_bal_bool:
                continue

            if open_executedQty == 0.0:  # open_executedQty 는 분명 정의됨
                self.income = 0
            else:
                sys_log.info('open order executed')
                sys_log.info("open_executedPrice_list : {}".format(open_executedPrice_list))
                real_balance = open_executedPrice_list[0] * open_executedQty
                sys_log.info("real_balance : {}".format(real_balance))  # define for pnl calc.

                #        1. save trade_log      #
                #        2. check str(res_df.index[-2]), back_sync entry on close     #
                #         3. back_pr 에서 res_df.index[-2] line 에 무엇을 기입하냐에 따라 달라짐
                # trade_log[str(res_df_open.index[self.config.trader_set.complete_index])] = [open_side, "open"]
                # trade_log[str(res_df.index[self.config.trader_set.complete_index])] = [ep, open_side, "entry"]
                #
                # with open(trade_log_fullpath, "wb") as dict_f:
                #     pickle.dump(trade_log, dict_f)
                #     sys_log.info("entry trade_log dumped !\n")

                # ------ set close side ------ #
                if open_side == OrderSide.BUY:
                    close_side = OrderSide.SELL
                else:
                    close_side = OrderSide.BUY

                # ------ param init. ------ #
                #   a. 아래의 조건문을 담을 변수가 필요함 - 병합 불가 (latest)
                #       i. => load_new_df2 는 1 -> 0 으로 변경됨
                use_new_df2 = 0
                if not self.config.tp_set.static_tp or not self.config.out_set.static_out:
                    use_new_df2 = 1    # for signal_out, dynamic_out & tp
                load_new_df2 = 1
                limit_tp = 0
                post_order_res_list = []
                # tp_executedQty = 0    # dynamic 미사용으로 invalid
                ex_dict = {}   # exist for ideal_ep
                tp_executedPrice_list, out_executedPrice_list = [], []
                cross_on = 0  # exist for signal_out (early_out)

                while 1:
                    if use_new_df2:
                        if load_new_df2:  # dynamic_out & tp phase
                            if self.config.trader_set.backtrade:
                                res_df = next(self.streamer)  # Todo, 무결성 검증 미진행
                                load_new_df2 = 0
                            else:
                                res_df, _, load_new_df2 = get_new_df(self, mode="CLOSE")

                            try:
                                res_df = self.utils_public.sync_check(res_df, self.config, order_side="CLOSE")
                                np_timeidx = np.array([intmin_np(date_) for date_ in res_df.index.to_numpy()])  # should be locate af. row_slice
                                res_df = self.utils_public.public_indi(res_df, self.config, np_timeidx, order_side="CLOSE")
                                res_df = self.utils.enlist_rtc(res_df, self.config, np_timeidx)
                                res_df = self.utils.enlist_tr(res_df, self.config, np_timeidx, mode="CLOSE")

                            except Exception as e:
                                sys_log.error("error in utils_ (load_new_df2 phase) : {}".format(e))
                                load_new_df2 = 1
                                continue

                            tp, out, tp_series, out_series = get_dynamic_tpout(self, res_df, open_side, tp, out)
                            #   series 형태는, dynamic_tp reorder 를 위한 tp change 여부를 확인하기 위함임

                    # --------- limit_tp check for order --------- #
                    # ------ 1. 첫 limit_tp order 진행햐야하는 상태 ------ #
                    if len(post_order_res_list) == 0:
                        limit_tp = 1
                    # else:
                    #     # ------ 2. dynamic_tp reorder - Todo, dynamic 미예정 (solved) ------ #
                    #     if not self.config.tp_set.static_tp:    # np.nan != np.nan
                    #         tp_series_np = tp_series.to_numpy()
                    #         if tp_series_np[self.config.trader_set.complete_index] != \
                    #                 tp_series_np[self.config.trader_set.complete_index - 1]:
                    #             #        1. 본래는, remaining 으로 open_executedQty refresh 진행함,
                    #             #        2. 지금은, 직접 구해야할 것
                    #             #           a. refreshedQty = open_executedQty - tp_executedQty : error 발생할때마다 recalc.
                    #             #        3. cancel post_order_res in list
                    #             dynamic_tp_executedPrice_list, tp_executedQty = cancel_order_list(self.config.trader_set.symbol, post_order_res_list)
                    #             limit_tp = 1

                    # ------- limit_tp order - while 내부에 있어서 on/off 로 진행 ------- #
                    if limit_tp:
                        # ------ 1. get realtime price, qty precision ------ #
                        price_precision, quantity_precision = get_precision(self.config.trader_set.symbol)
                        p_tps, p_qtys = get_p_tpqty(self, ep, tp, open_executedQty, price_precision, quantity_precision, close_side)

                        # ------ 2. p_tps limit_order ------ #
                        if not self.config.trader_set.backtrade:
                            while 1:
                                try:
                                    #   a. tp_exectuedQty 감산했던 이유 : dynamic_tp 의 경우 체결된 qty 제외
                                    #   b. reduceOnly = False for multi_position
                                    post_order_res_list = partial_limit_order_v4(self, p_tps, p_qtys, close_side, pos_side, open_executedQty, quantity_precision)
                                except Exception as e:
                                    sys_log.error("error in partial_limit_order_v4 : {}".format(e))
                                    time.sleep(self.config.trader_set.api_retry_term)
                                    #   Todo - tp_executedQty miscalc. -> dynamic 미예정이므로 miscalc issue 없음 (solved)
                                    #       1. -2019 : Margin is insufficient 으로 나타날 것으로 보임 - limit_order phase 에서 해결
                                    #       2. -4003 의 openexecQty 잘못된 가능성
                                    continue
                                else:
                                    sys_log.info("limit tp order enlisted : {}".format(datetime.now()))
                                    limit_tp = 0
                                    break

                    # ------------ limit_tp exec. & market_close check ------------ #
                    #            1. limit close (tp) execution check, every minute                 #
                    #            2. check market close signal, simultaneously
                    limit_done = 0
                    prev_exec_tp_len = 0
                    market_close_on = 0
                    log_out = None
                    load_new_df3 = 1
                    while 1:
                        # ------ 1. load_new_df3 every minutes ------ #
                        #           a. ohlc data, log_ts, back_pr wait_time 를 위해 필요함
                        if not use_new_df2:
                            if load_new_df3:
                                if self.config.trader_set.backtrade:
                                    res_df = next(self.streamer)  # Todo, 무결성 검증 미진행
                                    load_new_df3 = 0
                                else:
                                    res_df, _, load_new_df3 = get_new_df(self, calc_rows=False, mode="CLOSE")

                        # ------ 2. tp execution check ------ #
                        # Todo, execution_check 을 위한 backtrader 의 다른 logic 필요함
                        if not self.config.trader_set.backtrade:
                            all_executed, tp_executedPrice_list = check_limit_tp_exec(self, post_order_res_list, quantity_precision, return_price=True)

                            # ------ tp execution logging ------ #
                            # Todo, dynamic_tp 안만듬 - 미예정 (solved)
                            exec_tp_len = len(tp_executedPrice_list)
                            if prev_exec_tp_len != exec_tp_len:  # logging 기준
                                ex_dict[res_df.index[self.config.trader_set.complete_index]] = p_tps[prev_exec_tp_len:exec_tp_len]
                                prev_exec_tp_len = exec_tp_len
                                sys_log.info("ex_dict : {}".format(ex_dict))

                            if all_executed:
                                limit_done = 1
                                break

                        else:


                        # ------ 3. out check ------ #
                        try:
                            # Todo, barclose hl_out
                            market_close_on, log_out = check_hl_out(self, res_df, market_close_on, log_out, out, open_side)
                            if not market_close_on:  # log_out 갱신 방지
                                market_close_on, log_out, cross_on = check_signal_out(self, res_df, market_close_on, log_out, cross_on, open_side)

                            if market_close_on:
                                sys_log.info("market_close_on is True")
                                # ------ out execution logging ------ #
                                # market_close_on = True, log_out != None (None 도 logging 가능하긴함)
                                ex_dict[res_df.index[self.config.trader_set.complete_index]] = [log_out]
                                sys_log.info("ex_dict : {}".format(ex_dict))
                                break

                        except Exception as e:
                            sys_log.error('error in checking market_close_on : {}'.format(e))
                            continue

                        # ------ 3. bar_end phase - loop selection ------ #
                        # Todo, iterator 기준, 필요없어질 것
                        if datetime.now().timestamp() > datetime.timestamp(res_df.index[-1]):
                            if use_new_df2:
                                load_new_df2 = 1  # return to outer loop - get df2's data
                                break
                            else:
                                load_new_df3 = 1  # return to current loop
                        else:
                            time.sleep(self.config.trader_set.realtime_term)

                    # ------------ limit / market execution or load_new_df2 ------------ #
                    # ------ 1. all p_tps executed ------ #
                    if limit_done:
                        fee += self.config.trader_set.limit_fee
                        break
                    if not market_close_on:  # = load_new_df2
                        continue
                    else:
                        # ------ 2. hl & signal_out ------ #
                        # Todo, rm close_order, out_executedPrice_list = [out] if market_close_on (real_pr unnecessary)
                        fee += self.config.trader_set.market_fee
                        out_executedPrice_list = market_close_order_v2(self, post_order_res_list, close_side, pos_side, open_executedQty)
                        # market_close_order() 내부에서 close_qty 계산 진행함
                        break  # <--- break for all close order loop, break partial tp loop

                # ------ total_income() function confirming -> wait close confirm
                #           => we don't need this now, cause get_income_info_v2 ------ #
                # while 1:
                #     latest_close_timeidx = res_df.index[-1]
                #     if datetime.now().timestamp() > datetime.timestamp(latest_close_timeidx):
                #         break

                # ------------ calc_ideal_profit - market_order 시 ideal <-> real gap 발생 가능해짐 ------------ #
                #  Todo - p_qtys, 즉, non_tp 일 경우 error 발생할 거임
                ideal_profit, real_profit = calc_ideal_profit_v4(self, res_df, open_side, ep, ex_dict, open_executedPrice_list,
                                                                            tp_executedPrice_list, out_executedPrice_list, p_qtys, fee)
                # with open(trade_log_fullpath, "wb") as dict_f:
                #     pickle.dump(trade_log, dict_f)
                #     sys_log.info("exit trade_log dumped !")

                # ------------ get total income from this trade ------------ #
                self.income, self.accumulated_income, self.accumulated_profit, self.ideal_accumulated_profit = \
                    get_income_info_v2(self, real_balance, leverage, ideal_profit, real_profit)
