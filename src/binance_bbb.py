import argparse
import configparser
import datetime
import time

from binance.client import Client


def get_timestamp():
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


parser = argparse.ArgumentParser(description='Binance Balanced Buying Bot')

# Required positional arguments
parser.add_argument('crypto',
                    help="""The ticker of the crypto to spend (e.g. 'BTC',
                        'ETH', etc)""")
parser.add_argument('amount', type=float,
                    help="The quantity of the crypto to spend (e.g. 0.05)")

# Optional switches
parser.add_argument('-c', '--config',
                    default="settings_local.conf",
                    dest="config_file",
                    help="Override default config file location")

parser.add_argument('-t', '--test',
                    default=True,
                    dest="test_mode",
                    help="""Test API connection and portfolio config without
                        submitting actual orders""")

# TODO: input API key/secret from command line


args = parser.parse_args()
spending_crypto = args.crypto
spending_crypto_total_amount = args.amount
test_mode = args.test_mode

print("%s: STARTED: %s" % (get_timestamp(), args))

if test_mode:
    print("\n")
    print("\t================= TEST MODE =================")
    print("\t*                                           *")
    print("\t*     No actual trades being submitted!     *")
    print("\t*                                           *")
    print("\t=============================================")
    print("\n")

# Read settings
config = configparser.SafeConfigParser()
config.read(args.config_file)

config_section = 'API'
api_key = config.get(config_section, 'API_KEY')
api_secret = config.get(config_section, 'SECRET_KEY')
# aws_access_key_id = config.get(config_section, 'AWS_ACCESS_KEY_ID')
# aws_secret_access_key = config.get(config_section, 'AWS_SECRET_ACCESS_KEY')
# sns_topic = config.get(config_section, 'SNS_TOPIC')

portfolio_weights = {}
for buy_crypto, weight in config.items('portfolio_weights'):
    portfolio_weights[buy_crypto.upper()] = float(weight)
print(portfolio_weights)

# Instantiate public and auth API clients
client = Client(api_key, api_secret)

# Get exchange info (pairs available, min order sizes, etc.)
exchange_info = client.get_exchange_info()
pair_info = {}
for pair_obj in exchange_info.get("symbols"):
    # Only add the markets for our spending crypto
    if pair_obj.get("quoteAsset") == spending_crypto:
        pair_info[pair_obj.get("symbol")] = pair_obj


# First, what is the total weight specified in the portfolio?
total_weight = 0.0
for key, weight in portfolio_weights.items():
    total_weight += float(weight)


# Verify that each market exists (porfolio-crypto pairing) and that we'll meet
#   order minimums (minNotional value).
spending_amounts = {}
for buy_crypto, weight in portfolio_weights.items():
    market = buy_crypto + spending_crypto
    info = pair_info.get(market)
    if not info:
        raise Exception(
            "%s market not found in Binance exchange info" % market)

    if weight == 0.0:
        spending_crypto_value = 0.0
        step_size = 0.0
    else:
        # How much of the spending crypto will go towards this asset?
        spending_crypto_value = weight/total_weight * spending_crypto_total_amount

        # What's this asset's minimum purchase?
        for filter in info.get("filters"):
            if "minNotional" in filter:
                min_notional = float(filter.get("minNotional"))
            if "stepSize" in filter:
                step_size = float(filter.get("stepSize"))
        if not min_notional:
            raise Exception("minNotional not found in %s info" % market)
        if not min_notional:
            raise Exception("stepSize not found in %s info" % market)

        print("%s target order size: %f (minNotional: %f, stepSize: %f)" % (
            market,
            spending_crypto_value,
            min_notional,
            step_size)
        )

        if spending_crypto_value < min_notional:
            raise Exception(
                """Cannot purchase %s at weight %f. Resulting order of %f %s is
                    below the minNotional value of %f %s""" % (
                        buy_crypto,
                        weight,
                        spending_crypto_value,
                        spending_crypto,
                        min_notional,
                        spending_crypto)
            )

    spending_amounts[market] = {
        "amount": spending_crypto_value,
        "step_size": step_size
    }


for market, spending_amount in spending_amounts.items():
    # What are the current bids?
    amount = spending_amount.get("amount")
    step_size = spending_amount.get("step_size")

    if amount == 0.0:
        print("Skipping %s because weight is set to 0.0" % market)
        continue

    depth = client.get_order_book(symbol=market, limit=5)
    first_bid = float(depth.get("bids")[0][0])

    # How many can we buy with our target amount?
    quantity = amount / first_bid

    # Have to round the quantity to within the step_size (i.e. can't place an
    #   order for 0.0742 if stepSize is 0.01; would have to be rounded to 0.07)

    # Count the step_size's decimal precision; zero if greater than zero.
    decimals = len(str(round(1/step_size))) - 1
    quantity = round(quantity, decimals)
    print("%s: %f" % (market, quantity))

    print("placing %s order: %f @ %.8f %s. Total spend: %.8f %s" % (market, quantity, first_bid, spending_crypto, quantity*first_bid, spending_crypto))

    if test_mode:
        order = client.create_test_order(
            symbol=market,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity)

        print(order)

    else:
        raise Exception("Real buys aren't implemented yet!")


