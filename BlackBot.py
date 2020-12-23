import pywaves as pw
import datetime
import os
import configparser
import random
from colors import *


class BlackBot:
    def __init__(self):
        self.log_file = "grid.log"

        # main
        self.node = "https://nodes.wavesnodes.com"
        self.chain = "mainnet"
        self.matcher = "https://matcher.waves.exchange"
        self.order_fee = int(0.003 * 10 ** 8)
        self.order_lifetime = 29 * 86400  # 29 days

        # account
        self.private_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        self.wallet = None

        # market
        self.amount_asset_id = "WAVES"
        self.price_asset_id = "DG2xFkPdDwKUoBkzGAhQtLpSGzfXLiCYPEzeKH2Ad24p"  # USDN
        self.asset_pair = pw.AssetPair(pw.Asset(self.amount_asset_id), pw.Asset(self.price_asset_id))

        # grid
        self.interval = 0.005
        self.tranche_size = 150000000
        self.grid_levels = 20
        self.grid = ["-"] * self.grid_levels
        self.flexibility = 0
        self.type = "SYMMETRIC"
        self.base = "LAST"
        self.base_price = 0

        # logging
        self.logfile = "grid.log"

    def log(self, msg):
        timestamp = datetime.datetime.utcnow().strftime("%b %d %Y %H:%M:%S UTC")
        s = "[%s] %s:%s %s" % (timestamp, COLOR_WHITE, COLOR_RESET, msg)
        print(s)
        try:
            f = open(self.logfile, "a")
            f.write(s + "\n")
            f.close()
        except:
            pass

    def read_config(self, cfg_file):
        if not os.path.isfile(cfg_file):
            self.log("Missing config file")
            self.log("Exiting.")
            exit(1)

        try:
            config = configparser.RawConfigParser()
            config.read(cfg_file)

            # main
            self.node = config.get('main', 'node')
            self.chain = config.get('main', 'network')
            self.matcher = config.get('main', 'matcher')
            self.order_fee = config.getint('main', 'order_fee')
            self.order_lifetime = config.getint('main', 'order_lifetime')

            # account
            self.private_key = config.get('account', 'private_key')
            self.wallet = pw.Address(privateKey=self.private_key)

            # market
            self.amount_asset_id = config.get('market', 'amount_asset')
            self.price_asset_id = config.get('market', 'price_asset')
            self.asset_pair = pw.AssetPair(pw.Asset(self.amount_asset_id), pw.Asset(self.price_asset_id))

            # grid
            self.interval = config.getfloat('grid', 'interval')
            self.tranche_size = config.getint('grid', 'tranche_size')
            self.grid_levels = config.getint('grid', 'grid_levels')
            self.grid = ["-"] * self.grid_levels
            self.flexibility = config.getint('grid', 'flexibility')
            self.base = config.get('grid', 'base').upper()
            self.type = config.get('grid', 'type').upper()
            self.base_price = self.get_base_price()

            # logging
            self.logfile = config.get('logging', 'logfile')

            self.log("Config file '{0}' has been read".format(cfg_file))
            self.log("-" * 80)
            self.log("          Address : %s" % self.wallet.address)
            self.log("  Amount Asset ID : %s" % self.amount_asset_id)
            self.log("   Price Asset ID : %s" % self.price_asset_id)
            self.log("-" * 80)
            self.log("")

        except OSError:
            self.log("Error reading config file")
            self.log("Exiting.")
            exit(1)

    def get_last_price(self):
        try:
            last_trade_price = int(float(self.asset_pair.last()) * 10 ** (
                    self.asset_pair.asset2.decimals + (
                        self.asset_pair.asset2.decimals - self.asset_pair.asset1.decimals)))
        except:
            last_trade_price = 0
        return last_trade_price

    def get_base_price(self):
        base_price = 0
        try:
            if self.base.isdigit():
                base_price = int(self.base)
            elif self.base == "LAST":
                base_price = self.get_last_price()
            elif self.base == "BID":
                base_price = self.asset_pair.orderbook()['bids'][0]['price']
            elif self.base == "ASK":
                base_price = self.asset_pair.orderbook()['asks'][0]['price']
        except:
            base_price = 0
        if base_price == 0:
            self.log("Invalid BASE price")
            self.log("Exiting.")
            exit(1)
        return base_price

    def get_level_price(self, level):
        return int(self.base_price * (1 + self.interval) ** (level - self.grid_levels / 2))

    def init_grid(self, base_level):
        self.log("Grid initialisation [base price : %.*f]" % (
            self.asset_pair.asset2.decimals, float(self.base_price) / 10 ** self.asset_pair.asset2.decimals))
        self.log("Grid initialisation [base price : %.*f]" % (
            self.asset_pair.asset2.decimals,
            float(self.base_price) / 10 ** (self.asset_pair.asset2.decimals +
                                            (self.asset_pair.asset2.decimals - self.asset_pair.asset1.decimals))))

        if self.type == "SYMMETRIC" or self.type == "BIDS":
            for n in range(base_level - 1, -1, -1):
                self.buy(n)
        if self.type == "SYMMETRIC" or self.type == "ASKS":
            for n in range(base_level + 1, self.grid_levels):
                self.sell(n)

    def buy(self, level):
        if 0 <= level < self.grid_levels and (self.grid[level] == "" or self.grid[level] == "-"):
            price = self.get_level_price(level)
            price = int(price / 100) * 100
            price = round(price / 10 ** (self.asset_pair.asset2.decimals +
                                         (self.asset_pair.asset2.decimals - self.asset_pair.asset1.decimals)), 8)
            price = float(str(price))
            try:
                tranche_size = int(
                    self.tranche_size * (1 - (self.flexibility / float(200)) + (
                                random.random() * self.flexibility / float(100))))
                order = self.wallet.buy(self.asset_pair, tranche_size, price,
                                        matcherFee=self.order_fee, maxLifetime=self.order_lifetime)
                order_id = order.orderId
                self.log(">> [%03d] %s%-4s order  %18.*f%s" % (
                    level, COLOR_GREEN, 'BUY', self.asset_pair.asset2.decimals, price, COLOR_RESET))
            except:
                order_id = ""
            self.grid[level] = order_id

    def sell(self, level):
        if 0 <= level < self.grid_levels and (self.grid[level] == "" or self.grid[level] == "-"):
            price = self.get_level_price(level)
            price = int(price / 100) * 100
            price = round(price / 10 ** (self.asset_pair.asset2.decimals +
                                         (self.asset_pair.asset2.decimals - self.asset_pair.asset1.decimals)), 8)
            price = float(str(price))
            try:
                tranche_size = int(
                    self.tranche_size * (1 - (self.flexibility / float(200)) + (
                                random.random() * self.flexibility / float(100))))

                order = self.wallet.sell(self.asset_pair, tranche_size, price,
                                         maxLifetime=self.order_lifetime, matcherFee=self.order_fee)
                order_id = order.orderId
                self.log(">> [%03d] %s%-4s order  %18.*f%s" % (
                    level, COLOR_RED, 'SELL', self.asset_pair.asset2.decimals, price, COLOR_RESET))
            except:
                order_id = ""
            self.grid[level] = order_id

