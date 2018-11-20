# Binance Balanced Buying Bot (binance_bbb) 

A Roll-Your-Own approach to setting up your own customized Binance index fund to buy into using a dollar-cost-averaging investing philosophy.

Set up a customized basket of target cryptos and relative weights. Then the `binance_bbb` will buy each of them for you at the specified ratios.

## Note on Binance market orders
On many exchanges a market order pays higher fees than limit orders. But Binance fees are the same whether you're the maker or the taker. So this bot just places instantly-fulfilled market orders. There's usually sufficient liquidity to assume your order will be filled without the price moving much in the milliseconds it takes to check the market and then place the order.

The only way to reduce Binance fees is to hold their BNB token in your account (currently 0.1% fees become 0.075%).


# Setup
- Requires Python 3.7
- python3 virtualenv recommended

## Dependencies

Install the python dependencies via:
```
pip install -r src/requirements.txt
```

_Note: depending on your setup you might have to use `pip3 install -r src/requirements.txt`_

## Create and store API keys
Create a new API key on Binance and take careful note of the api key and api secret. I strongly recommend that you also enable the option to "Restrict access to trusted IPs only".

In the `conf/` dir rename the dummy `settings.conf` to `settings_local.conf`. Open it with 
a text editor and update it with your actual Binance API keys:
```
[API]
API_KEY = lkasjdfklasdfklasdf
SECRET_KEY = lkasdjflksadjflkasjdflkasdfs


[AWS]
# Optional. Delete this section if you aren't using AWS SNS email notifications
SNS_TOPIC = enter:your:arn:here
AWS_ACCESS_KEY_ID = ABCDEFGHIJKLMNOP
AWS_SECRET_ACCESS_KEY = foobarfoobarfoobar
```
_As noted you can also customize or omit AWS SNS notification integration._

Also rename the dummy `portfolio.conf` to `portfolio_local.conf` for the next step.

# Customize your portfolio
Open your `portfolio_local.conf` in a text editor. It will initially contain some example dummy data:
```
[portfolio_weights]
ABC = 1.0
XYZ = 1.1
FOO = 0.9
BAR = 0.0
```

Update the list to the actual crypto ticker labels that you'd like to buy (e.g. NEO, EOS, ZRX). Then specify a weighting for each crypto. The weights determine the ratio of how much of your order will be for each crypto.

Example 1: Equal amounts:
```
[portfolio_weights]
NEO = 1.0
GAS = 1.0
ONT = 1.0
```
If you buy a total of 0.1 BTC worth of this portfolio, then each of these three cryptos would generate a ~0.0333 BTC order.

Example 2: Varying weights:
```
[portfolio_weights]
AST = 1.0
LRC = 2.5
ZRX = 0.5
```
In this case AST would make up ```1.0 / (1.0 + 2.5 + 0.5) = 0.25``` of the order.

Example 3: Disabling a crypto:
```
[portfolio_weights]
EOS = 0.0
ADA = 1.0
XLM = 1.0
```
Because EOS' weight is set to 0.0 the portfolio will ignore it and just follow the weights specified for the other two cryptos.

# Usage
```
usage: binance_bbb.py [-h] [-c SETTINGS_CONFIG_FILE]
                      [-p PORTFOLIO_CONFIG_FILE]
                      [-m PORTFOLIO_MANUAL_OVERRIDE] [-l] [-j]
                      crypto amount

Binance Balanced Buying Bot

positional arguments:
  crypto                The ticker of the crypto to spend (e.g. 'BTC', 'ETH',
                        etc)
  amount                The quantity of the crypto to spend (e.g. 0.05)

optional arguments:
  -h, --help            show this help message and exit
  -c SETTINGS_CONFIG_FILE, --settings_config SETTINGS_CONFIG_FILE
                        Override default settings config file location
  -p PORTFOLIO_CONFIG_FILE, --portfolio_config PORTFOLIO_CONFIG_FILE
                        Override default portfolio config file location
  -m PORTFOLIO_MANUAL_OVERRIDE, --manual_portfolio PORTFOLIO_MANUAL_OVERRIDE
                        Override portfolio conf and buy the comma-separated
                        cryptos listed
  -l, --live            Submit live orders. When omitted, just tests API
                        connection, portfolio weights, and amount without
                        submitting actual orders
  -j, --job             Suppress the confirmation step before submitting
                        actual orders
```


# Testing your portfolio

## Minimum notional values
Binance specifies a minimum buy order value for each crypto (aka `minNotional`). Let's say you're looking to buy equal amounts of 10 different cryptos and only want to spend 0.005 BTC altogether. Obviously each order's notional value will then be 0.0005 BTC.

But the `minNotional` for BTC orders is 0.001; Binance will not let you place an order whose value is smaller than that.


## Manual/cron buys
Use the `-m` or `--manual_portfolio` command line option to specify a comma-separated list of cryptos in lieu of your customized portfolio configuration. This option is intended to allow this bot to be used as a simple, schedulable buying bot for a single crypto or basic portfolio of cryptos. In this mode all manually-specified cryptos are given an equal weighting.

For example, you might have a new crypto that you want to build a position in so you'll want to set it on its own dollar-cost averaging buy in schedule, separate from your broader portfolio schedule.

Typically you'd set this up as its own cron job:
```
* */6 * * * /your/virtualenv/path/bin/python -u /your/binance_bbb/path/src/binance_bbb.py BTC 0.00125 -c /your/settings/path/your_settings_file.conf -m ICX,WAN -j -l >> /your/cron/log/path/cron.log 2>&1
```
In this case the specified 0.00125 BTC will be evenly divided between the two manual portfolio cryptos and will repeat this same buy every six hours.


#### Mac notes
Edit the crontab:
```
env EDITOR=nano crontab -e
```

View the current crontab:
```
crontab -l
```


## Disclaimer
_I built this to execute my own micro dollar cost-averaging crypto buys. Use and modify it at your own risk. This is also not investment advice. I am not an investment advisor. You should do your own research and invest in the way that best suits your needs and risk profile.  Good luck and HODL strong._


# Tips
If you found this useful, send me some digital love
- ETH: 0xb581603e2C4eb9a9Ece4476685f0600CeB472241
- BTC: 13u1YbpSzNsvVpPMyzaDAfzP2jRcZUwh96
- LTC: LMtPGHCQ3as6AEC9ueX4tVQw7GvHegv3fA
- DASH: XhCnytvKkV44Mn5WeajGfaifgY8vGtamW4
