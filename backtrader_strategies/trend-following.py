import backtrader as bt
from backtrader_functions import GenericCSV, EWMAC
import pandas as pd
import numpy as np


# Create a Stratey
class TrendStrategy(bt.Strategy):

    params = (
              ('fast_period', 2),
              ('vol_lookback', 36),
              ('ewm_std', True))

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.record = pd.DataFrame()

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.start_trade = None
        self.end_trade = None

        self.scale = True

        self.forecasts = [EWMAC(plot=True,
                                fast_period=self.p.fast_period ** x,
                                slow_period=self.p.fast_period ** x * 4,
                                vol_lookback=self.p.vol_lookback,
                                scale=self.scale
                                ) for x in range(1, 7)]

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        pass
        # Simply log the closing price of the series from the reference
        # self.log('Position: %.0f, Close: %.2f, Fast: %.2f, Slow: %.2f, Forecast: %.2f' % (self.position.size,
        #                                                                                   self.dataclose[0],
        #                                                                                   self.fast[0],
        #                                                                                   self.slow[0],
        #                                                                                   self.forecast[0],
        #                                                                                      ))
        # record = pd.DataFrame(np.array([[self.data.datetime.datetime(),
        #                                  self.position.size,
        #                                  self.dataclose[0],
        #                                  self.fast[0],
        #                                  self.slow[0],
        #                                  self.forecast[0]]]),
        #                       columns=['timestamp', 'position', 'close', 'fast', 'slow', 'forecast'])
        #
        # self.record = self.record.append(record)
        # EMWA
        # if not self.position:
        #
        #     if self.fast > self.slow and self.fast[-1] <= self.slow[-1]:
        #         self.order = self.buy()
        #         self.log('BUY CREATE, %.2f' % self.order.created.price)
        #
        #     if self.fast < self.slow and self.fast[-1] >= self.slow[-1]:
        #         self.order = self.sell()
        #         self.log('SELL CREATE, %.2f' % self.order.created.price)
        #
        # if self.position.size > 0:
        #     if self.fast < self.slow:
        #         self.order = self.sell(size=2)
        #
        # if self.position.size < 0:
        #     if self.fast > self.slow:
        #         self.order = self.buy(size=2)


class TrendStrategyNoScale(TrendStrategy):
    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.start_trade = None
        self.end_trade = None

        self.scale = False

        self.forecasts = [EWMAC(plot=True,
                                fast_period=self.p.fast_period ** x,
                                slow_period=self.p.fast_period ** x * 4,
                                vol_lookback=self.p.vol_lookback,
                                scale=self.scale
                                ) for x in range(1, 7)]


def get_forecast_scalars():
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TrendStrategyNoScale)
    data0 = GenericCSV(dataname='data/BTCUSDT-truncated.csv')
    cerebro.resampledata(data0, timeframe=bt.TimeFrame.Minutes, compression=60)
    thestrats = cerebro.run(tradehistory=True)
    thestrat = thestrats[0]
    forecasts = thestrat.forecasts
    string = ''
    for f in forecasts:
        fast_period = f.params.fast_period
        scalar = round(10 / np.nanmean(f.array), 2)
        string = string + 'l%.0f_%.0f=%.2f, ' % (fast_period, fast_period*4, scalar)

    print(string[:-2])

# get_forecast_scalars()

if __name__ == '__main__':
    cerebro = bt.Cerebro()

    cerebro.addstrategy(TrendStrategy)
    data0 = GenericCSV(dataname='data/BTCUSDT.csv')
    cerebro.resampledata(data0, timeframe=bt.TimeFrame.Minutes, compression=60)

    cerebro.broker.set_cash(100000)
    cerebro.broker.setcommission(commission=0.04 / 100)
    # cerebro.addwriter(bt.WriterFile, csv=True, out='logs.csv')

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    # print(10 / np.nanmean(cerebro.runningstrats[0].forecast.array))

    cerebro.plot()


