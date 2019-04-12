import argparse
import configparser
import datetime
import time
import boto3

from binance.exceptions import BinanceAPIException
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
parser.add_argument('-c', '--settings_config',
                    default="conf/settings_local.conf",
                    dest="settings_config_file",
                    help="Override default settings config file location")

parser.add_argument('-p', '--portfolio_config',
                    default="conf/portfolio_local.conf",
                    dest="portfolio_config_file",
                    help="Override default portfolio config file location")

parser.add_argument('-m', '--manual_portfolio',
                    dest="portfolio_manual_override",
                    help="""Override portfolio conf and buy the comma-separated
cryptos listed""")

parser.add_argument('-l', '--live',
                    action='store_true',
                    default=False,
                    dest="live_mode",
                    help="""Submit live orders. When omitted, just tests API
                        connection, portfolio weights, and amount without
                        submitting actual orders""")

parser.add_argument('-j', '--job',
                    action='store_true',
                    default=False,
                    dest="job_mode",
                    help="""Suppress the confirmation step before submitting
actual orders""")

# TODO: input API key/secret from command line


args = parser.parse_args()
spending_crypto = args.crypto
spending_crypto_total_amount = args.amount
live_mode = args.live_mode
job_mode = args.job_mode

print("%s: STARTED: %s" % (get_timestamp(), args))

if not live_mode:
    print("\n")
    print("\t================= NOT in Live mode =================")
    print("\t*                                                  *")
    print("\t*        No actual trades being submitted!         *")
    print("\t*                                                  *")
    print("\t====================================================")
    print("\n")

# Read settings
config = configparser.SafeConfigParser()
config.read(args.settings_config_file)

api_key = config.get('API', 'API_KEY')
api_secret = config.get('API', 'SECRET_KEY')

try:
    sns_topic = config.get('AWS', 'SNS_TOPIC')
    aws_access_key_id = config.get('AWS', 'AWS_ACCESS_KEY_ID')
    aws_secret_access_key = config.get('AWS', 'AWS_SECRET_ACCESS_KEY')
except configparser.NoSectionError:
    sns_topic = None

if sns_topic:
    # Prep boto SNS client for email notifications
    sns = boto3.client(
        "sns",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="us-east-1"     # N. Virginia
    )


portfolio_weights = {}

if args.portfolio_manual_override:
    for buy_crypto in args.portfolio_manual_override.split(','):
        # Manually specified override cryptos all get set with equal weighting
        portfolio_weights[buy_crypto] = 1.0

else:
    try:
        config = configparser.SafeConfigParser()
        config.read(args.portfolio_config_file)

        for buy_crypto, weight in config.items('portfolio_weights'):
            portfolio_weights[buy_crypto.upper()] = float(weight)
    except configparser.NoSectionError:
        print("Your portfolio config is not correctly configured")
        exit()

print(portfolio_weights)

# Instantiate API client
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

        print(
            f"{market} target order size: " +
            f"{spending_crypto_value:.8f} {spending_crypto} " +
            f"(minNotional: {min_notional}, stepSize: {step_size:.2f})"
        )

        if spending_crypto_value < min_notional:
            raise Exception(
                f"Cannot purchase {buy_crypto} at weight {weight}. " +
                f"Resulting order of {spending_crypto_value} {spending_crypto} " +
                f"is below the minNotional value of {min_notional} {spending_crypto}"
            )

    spending_amounts[market] = {
        "buy_crypto": buy_crypto,
        "amount": spending_crypto_value,
        "step_size": step_size
    }

if live_mode and not job_mode:
    print("\n================================================\n")
    response = input("\tLive purchase! Confirm Y/[n]: ")
    if response != 'Y':
        print("Exiting without submitting orders.")
        exit()


total_crypto_spent = 0.0
purchase_summary = ""
for market, spending_amount in spending_amounts.items():
    # What are the current bids?
    buy_crypto = spending_amount.get("buy_crypto")
    amount = spending_amount.get("amount")
    step_size = spending_amount.get("step_size")

    if amount == 0.0:
        print(f"Skipping {market} because weight is set to 0.0")
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
    order_amount = quantity*first_bid

    print("placing %s order: %5.2f @ %.8f %s. Total spend: %.8f %s" % (
        market,
        quantity,
        first_bid,
        spending_crypto,
        order_amount,
        spending_crypto)
    )

    if not live_mode:
        order = client.create_test_order(
            symbol=market,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity)

        if order:
            print(order)

    else:
        try:
            order = client.order_market_buy(
                symbol=market,
                quantity=quantity)
        except BinanceAPIException as e:
            print(f'Unable to place {market} order: {e}')
            if sns_topic and live_mode:
                sns.publish(
                    TopicArn=sns_topic,
                    Subject=f'Unable to place {market} order',
                    Message=str(e)
                )
            exit()

    purchase_summary += "%s: %5.2f @ %.8f %s = %.6f %s\n" % (
        buy_crypto,
        quantity,
        first_bid,
        spending_crypto,
        order_amount,
        spending_crypto)
    total_crypto_spent += order_amount


if sns_topic and live_mode:
    if args.portfolio_manual_override:
        subject = f"{total_crypto_spent:.4f} {spending_crypto} manual {args.portfolio_manual_override} buy order completed"
    else:
        subject = f"{total_crypto_spent:.4f} {spending_crypto} portfolio buy order completed"
    sns.publish(
        TopicArn=sns_topic,
        Subject=subject,
        Message=purchase_summary
    )


print("\n================================================")
print(purchase_summary)
print(f"Total orders placed: {total_crypto_spent:.8f} {spending_crypto}")
if not live_mode:
    print("(NOT in live mode - no actual orders placed!)")
