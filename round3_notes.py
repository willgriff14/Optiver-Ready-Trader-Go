# Import required libraries
import asyncio
import itertools
import numpy as np

from typing import List

# Import specific functions and constants from ready_trader_go
from ready_trader_go import BaseAutoTrader, Instrument, Lifespan, MAXIMUM_ASK, MINIMUM_BID, Side

# Define constants for the trading strategy
LOT_SIZE = 25
POSITION_LIMIT = 50
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS

# Define the AutoTrader class which inherits from BaseAutoTrader
class AutoTrader(BaseAutoTrader):

    # Static lists to keep track of the historical bid and ask prices for both futures and ETFs
    fut_bid_hist = [0,0,0]
    fut_ask_hist = [0,0,0]
    etf_bid_hist = [0,0,0]
    etf_ask_hist = [0,0,0] 

    # Initialization method for the AutoTrader class
    def __init__(self, loop: asyncio.AbstractEventLoop, team_name: str, secret: str):
        super().__init__(loop, team_name, secret)  # Call to the parent's initializer
        self.order_ids = itertools.count(1)  # Create a counter for unique order IDs
        self.bids = set()  # Set to track bid orders
        self.asks = set()  # Set to track ask orders
        # Initialize various variables and properties used in the trading logic to zero
        self.ask_id = self.ask_price = self.bid_id = self.bid_price = self.position = self.ask_id2 = self.ask_price2 = self.bid_id2 = self.bid_price2 = self.position2 = self.ask_id3 = self.ask_price3 = self.bid_id3 = self.bid_price3 = self.position3 = 0
        # Initialize historical bid and ask price variables
        self.fut_bid_prev, self.fut_ask_prev, self.etf_bid_prev, self.etf_ask_prev = self.fut_bid_hist, self.fut_ask_hist, self.etf_bid_hist, self.etf_ask_hist

    # Method to handle order book updates
    def on_order_book_update_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                                     ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        # Log received order book details
        self.logger.info("received order book for instrument %d with sequence number %d", instrument,
                         sequence_number)
        
        # Check if the instrument is FUTURE
        if instrument == Instrument.FUTURE:
            
            x = y = 0
            # Trading logic to decide buying/selling based on historical and current prices
            if ask_prices[0] > self.fut_ask_prev[-1] > self.etf_ask_prev[-1] and self.fut_bid_prev[-2] > self.etf_ask_prev[-2]:
                x = 2
            if ask_prices[0] > self.fut_ask_prev[-1] > self.etf_ask_prev[-1] and self.fut_bid_prev[-2] > self.etf_ask_prev[-2]:
                x = -2
            if self.etf_bid_prev[-1] - self.fut_bid_prev[-1] > 200:
                y = -100
            if self.etf_bid_prev[-1] - self.fut_bid_prev[-1] < -200:
                y = 100

            # Adjust prices based on position and other trading logic
            price_adjustment,price_adjustment2= - (self.position // LOT_SIZE) * TICK_SIZE_IN_CENTS, - (self.position2 // LOT_SIZE) * TICK_SIZE_IN_CENTS
            new_bid_price, new_ask_price = bid_prices[2+x] + price_adjustment, ask_prices[2+x] + price_adjustment
            new_bid_price2, new_ask_price2 = bid_prices[2] + y + price_adjustment2, ask_prices[2] + y + price_adjustment2

            # Place buy order based on calculated bid price and other conditions
            if self.bid_id3 == 0 and new_bid_price2+100 != 0 and self.position3 < POSITION_LIMIT:
                self.bid_id3 = next(self.order_ids)  # Get a new order ID
                self.bid_price3 = new_bid_price2+100
                self.send_insert_order(self.bid_id3, Side.BUY, new_bid_price2+100, 20, Lifespan.FILL_AND_KILL)  # Send the buy order
                self.bids.add(self.bid_id3)  # Add the order ID to the set of bid orders

          # Check if a SELL order should be placed for the 3rd trading logic, based on the calculated ask price and other conditions
          if self.ask_id3 == 0 and new_ask_price2-100 != 0 and self.position3 > -POSITION_LIMIT:
            # Generate a new order ID for the sell order
              self.ask_id3 = next(self.order_ids)
              self.ask_price3 = new_ask_price2-100
              # Place a new SELL order with the calculated ask price
              self.send_insert_order(self.ask_id3, Side.SELL, new_ask_price2-100, 20, Lifespan.FILL_AND_KILL)
              # Add the order ID to the set of ask orders
              self.asks.add(self.ask_id3)

          # Cancel existing BUY orders for the 1st and 2nd trading logics if the new bid price is different
          if self.bid_id != 0 and new_bid_price not in (self.bid_price, 0):
              self.send_cancel_order(self.bid_id)
              self.bid_id = 0

          if self.bid_id2 != 0 and new_bid_price2 not in (self.bid_price2, 0):
              self.send_cancel_order(self.bid_id2)
              self.bid_id2 = 0

          # Cancel existing SELL orders for the 1st and 2nd trading logics if the new ask price is different
          if self.ask_id != 0 and new_ask_price not in (self.ask_price, 0):
              self.send_cancel_order(self.ask_id)
              self.ask_id = 0

          if self.ask_id2 != 0 and new_ask_price2 not in (self.ask_price2, 0):
              self.send_cancel_order(self.ask_id2)
              self.ask_id2 = 0

          # Place new BUY orders for the 1st and 2nd trading logics based on the calculated bid price and other conditions
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

          # Place new SELL orders for the 1st and 2nd trading logics based on the calculated ask price and other conditions
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

            # Update historical bid and ask price lists for FUTURE instrument
          if instrument == Instrument.FUTURE:
              AutoTrader.fut_bid_hist.append(bid_prices[0])
              AutoTrader.fut_ask_hist.append(ask_prices[0])

          # Update historical bid and ask price lists for ETF instrument
          if instrument == Instrument.ETF:
              AutoTrader.etf_bid_hist.append(bid_prices[0])
              AutoTrader.etf_ask_hist.append(ask_prices[0])

      # Method to handle order fill messages, which notify when an order has been executed
       def on_order_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
          # Log the details of the filled order
           self.logger.info("received order filled for order %d with price %d and volume %d", client_order_id, price, volume)

          # Check if the filled order was a BUY order
          if client_order_id in self.bids:
              # Update the positions for the 1st, 2nd, and 3rd trading logics
              self.position += volume
              self.position2 += volume
              self.position3 += volume
              # Send a hedge order, which is a SELL order with specified price and volume
              self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)

          # Check if the filled order was a SELL order
          elif client_order_id in self.asks:
              # Update the positions for the 1st, 2nd, and 3rd trading logics
              self.position -= volume
              self.position2 -= volume
              self.position3 -= volume
              # Send a hedge order, which is a BUY order with specified price and volume
              self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)

      # Method to handle error messages, which notify when there's a problem with an order
      def on_error_message(self, client_order_id: int, error_message: bytes) -> None:
          # Log the error message
          self.logger.warning("error with order %d: %s", client_order_id, error_message.decode())
          # Check if there's an active order with the provided order ID
          if client_order_id != 0 and (client_order_id in self.bids or client_order_id in self.asks):
              # Request order status update
              self.on_order_status_message(client_order_id, 0, 0, 0)

      # Method to handle hedge order fill messages, which notify when a hedge order has been executed
      def on_hedge_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
          # Log the details of the filled hedge order
          self.logger.info("received hedge filled for order %d with average price %d and volume %d", client_order_id,
                     price, volume)

      # Method to receive updates about the status of an order
      def on_order_status_message(self, client_order_id: int, fill_volume: int, remaining_volume: int, fees: int) -> None:
          # Log the order status
          self.logger.info("received order status for order %d with fill volume %d remaining %d and fees %d",
                           client_order_id, fill_volume, remaining_volume, fees)
      # If there's no volume remaining for the order, reset the associated order ID
          if remaining_volume == 0:
              if client_order_id == self.bid_id:
                self.bid_id = 0
              elif client_order_id == self.ask_id:
                 self.ask_id = 0

               # Remove the order ID from the bids and asks sets
              self.bids.discard(client_order_id)
              self.asks.discard(client_order_id)

      # Method to handle trade ticks messages, which provide updates on market trades
      def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int], ask_volumes: List[int],
                           bid_prices: List[int], bid_volumes: List[int]) -> None:
          # Log the trade ticks message
          self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument, sequence_number)
