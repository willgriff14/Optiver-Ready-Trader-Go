import asyncio
import itertools
import numpy as np

from typing import List

from ready_trader_go import BaseAutoTrader, Instrument, Lifespan, MAXIMUM_ASK, MINIMUM_BID, Side


LOT_SIZE = 25
POSITION_LIMIT = 50
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS


class AutoTrader(BaseAutoTrader):

    fut_bid_hist = [0,0,0]
    fut_ask_hist = [0,0,0]
    etf_bid_hist = [0,0,0]
    etf_ask_hist = [0,0,0] 

    def __init__(self, loop: asyncio.AbstractEventLoop, team_name: str, secret: str):
        super().__init__(loop, team_name, secret)
        self.order_ids = itertools.count(1)
        self.bids = set()
        self.asks = set()
        self.ask_id = self.ask_price = self.bid_id = self.bid_price = self.position = self.ask_id2 = self.ask_price2 = self.bid_id2 = self.bid_price2 = self.position2 = self.ask_id3 = self.ask_price3 = self.bid_id3 = self.bid_price3 = self.position3 = 0
        self.fut_bid_prev, self.fut_ask_prev, self.etf_bid_prev, self.etf_ask_prev = self.fut_bid_hist, self.fut_ask_hist, self.etf_bid_hist, self.etf_ask_hist

    def on_order_book_update_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                                     ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        self.logger.info("received order book for instrument %d with sequence number %d", instrument,
                         sequence_number)
        
        if instrument == Instrument.FUTURE:
            
            x = y = 0
            if ask_prices[0] > self.fut_ask_prev[-1] > self.etf_ask_prev[-1] and self.fut_bid_prev[-2] > self.etf_ask_prev[-2]:
                x = 2
            if ask_prices[0] > self.fut_ask_prev[-1] > self.etf_ask_prev[-1] and self.fut_bid_prev[-2] > self.etf_ask_prev[-2]:
                x = -2
            if self.etf_bid_prev[-1] - self.fut_bid_prev[-1] > 200:
                y = -100
            if self.etf_bid_prev[-1] - self.fut_bid_prev[-1] < -200:
                y = 100

            price_adjustment,price_adjustment2= - (self.position // LOT_SIZE) * TICK_SIZE_IN_CENTS, - (self.position2 // LOT_SIZE) * TICK_SIZE_IN_CENTS
            new_bid_price, new_ask_price = bid_prices[2+x] + price_adjustment, ask_prices[2+x] + price_adjustment
            new_bid_price2, new_ask_price2 = bid_prices[2] + y + price_adjustment2, ask_prices[2] + y + price_adjustment2

            if self.bid_id3 == 0 and new_bid_price2+100 != 0 and self.position3 < POSITION_LIMIT:
                self.bid_id3 = next(self.order_ids)
                self.bid_price3 = new_bid_price2+100
                self.send_insert_order(self.bid_id3, Side.BUY, new_bid_price2+100, 20, Lifespan.FILL_AND_KILL)
                self.bids.add(self.bid_id3)
            
            if self.ask_id3 == 0 and new_ask_price2-100 != 0 and self.position3 > -POSITION_LIMIT:
                self.ask_id3 = next(self.order_ids)
                self.ask_price3 = new_ask_price2-100
                self.send_insert_order(self.ask_id3, Side.SELL, new_ask_price2-100, 20, Lifespan.FILL_AND_KILL)
                self.asks.add(self.ask_id3)

            if self.bid_id != 0 and new_bid_price not in (self.bid_price, 0):
                self.send_cancel_order(self.bid_id)
                self.bid_id = 0
            
            if self.bid_id2 != 0 and new_bid_price2 not in (self.bid_price2, 0):
                self.send_cancel_order(self.bid_id2)
                self.bid_id2 = 0

            if self.ask_id != 0 and new_ask_price not in (self.ask_price, 0):
                self.send_cancel_order(self.ask_id)
                self.ask_id = 0
            
            if self.ask_id2 != 0 and new_ask_price2 not in (self.ask_price2, 0):
                self.send_cancel_order(self.ask_id2)
                self.ask_id2 = 0
    
            if self.bid_id == 0 and new_bid_price != 0 and self.position < POSITION_LIMIT:
                self.bid_id = next(self.order_ids)
                self.bid_price = new_bid_price
                self.send_insert_order(self.bid_id, Side.BUY, new_bid_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.bids.add(self.bid_id)

            if self.bid_id2 == 0 and new_bid_price2 != 0 and self.position2 < POSITION_LIMIT:
                self.bid_id2 = next(self.order_ids)
                self.bid_price2 = new_bid_price2
                self.send_insert_order(self.bid_id2, Side.BUY, new_bid_price2, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.bids.add(self.bid_id2)

            if self.ask_id == 0 and new_ask_price != 0 and self.position > -POSITION_LIMIT:
                self.ask_id = next(self.order_ids)
                self.ask_price = new_ask_price
                self.send_insert_order(self.ask_id, Side.SELL, new_ask_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.asks.add(self.ask_id)
            
            if self.ask_id2 == 0 and new_ask_price2 != 0 and self.position2 > -POSITION_LIMIT:
                self.ask_id2 = next(self.order_ids)
                self.ask_price2 = new_ask_price2
                self.send_insert_order(self.ask_id2, Side.SELL, new_ask_price2, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.asks.add(self.ask_id2)
        
            AutoTrader.fut_bid_hist.append(bid_prices[0])
            AutoTrader.fut_ask_hist.append(ask_prices[0])
        
        if instrument == Instrument.ETF:
            AutoTrader.etf_bid_hist.append(bid_prices[0])
            AutoTrader.etf_ask_hist.append(ask_prices[0])

    def on_order_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        self.logger.info("received order filled for order %d with price %d and volume %d", client_order_id,
                         price, volume)
        
        if client_order_id in self.bids:
            self.position += volume
            self.position2 += volume
            self.position3 += volume
            self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)

        elif client_order_id in self.asks:
            self.position -= volume
            self.position2 -= volume
            self.position3 -= volume
            self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)


    def on_error_message(self, client_order_id: int, error_message: bytes) -> None:
        self.logger.warning("error with order %d: %s", client_order_id, error_message.decode())
        if client_order_id != 0 and (client_order_id in self.bids or client_order_id in self.asks):
            self.on_order_status_message(client_order_id, 0, 0, 0)

    def on_hedge_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        self.logger.info("received hedge filled for order %d with average price %d and volume %d", client_order_id,
                         price, volume)

    def on_order_status_message(self, client_order_id: int, fill_volume: int, remaining_volume: int,
                                fees: int) -> None:
        self.logger.info("received order status for order %d with fill volume %d remaining %d and fees %d",
                         client_order_id, fill_volume, remaining_volume, fees)
        if remaining_volume == 0:
            if client_order_id == self.bid_id:
                self.bid_id = 0
            elif client_order_id == self.ask_id:
                self.ask_id = 0

            # It could be either a bid or an ask
            self.bids.discard(client_order_id)
            self.asks.discard(client_order_id)



    def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                               ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)