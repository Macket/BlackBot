import time
import os
import sys
import pywaves as pw

from colors import *
from BlackBot import BlackBot

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


def main():
    bot = BlackBot()

    cfg_file = ""
    if len(sys.argv) >= 2:
        cfg_file = sys.argv[1]
    if not os.path.isfile(cfg_file):
        bot.log("Missing config file")
        bot.log("Exiting.")
        exit(1)

    bot.read_config(cfg_file)
    pw.setNode(node=bot.node, chain=bot.chain)
    pw.setMatcher(node=bot.matcher)

    # grid list with GRID_LEVELS items. item n is the ID of the order placed at the price calculated with this formula
    # price = int(basePrice * (1 + INTERVAL) ** (n - GRID_LEVELS / 2))

    bot.log("Cancelling open orders...")
    bot.wallet.cancelOpenOrders(bot.asset_pair)  # cancel all open orders on the specified pair

    bot.log("Deleting order history...")
    bot.wallet.deleteOrderHistory(bot.asset_pair)  # delete order history on the specified pair
    bot.log("")

    last_level = int(bot.grid_levels / 2)

    # loop forever
    while True:
        # attempt to retrieve order history from matcher
        try:
            history = bot.wallet.getOrderHistory(bot.asset_pair)
        except:
            history = []

        if history:
            # loop through all grid levels
            # first all ask levels from the lowest ask to the highest -> range(grid.index("") + 1, len(grid))
            # then all bid levels from the highest to the lowest -> range(grid.index("") - 1, -1, -1)
            for n in list(range(last_level + 1, len(bot.grid))) + list(range(last_level - 1, -1, -1)):

                # find the order with id == grid9*-+[n] in the history list

                order = [item for item in history if item['id'] == bot.grid[n]]
                status = order[0].get("status") if order else ""
                if status == "Filled":
                    bot.wallet.deleteOrderHistory(bot.asset_pair)
                    bot.grid[n] = ""
                    last_level = n
                    filled_price = order[0].get("price")
                    filled_type = order[0].get("type")
                    bot.log("## [%03d] %s%-4s Filled %18.*f%s" % (
                        n, COLOR_BLUE, filled_type.upper(), bot.asset_pair.asset2.decimals,
                        float(filled_price) / 10 ** (bot.asset_pair.asset2.decimals + (
                                bot.asset_pair.asset2.decimals - bot.asset_pair.asset1.decimals)), COLOR_RESET))

                    if filled_type == "buy":
                        bot.sell(n+1)
                    elif filled_type == "sell":
                        bot.buy(n - 1)

                # attempt to place again orders for empty grid levels or cancelled orders
                elif (status == "" or status == "Cancelled") and bot.grid[n] != "-":
                    bot.grid[n] = ""
                    if n > last_level:
                        bot.sell(n)
                    elif n < last_level:
                        bot.buy(n)
        time.sleep(5)


if __name__ == "__main__":
    main()
