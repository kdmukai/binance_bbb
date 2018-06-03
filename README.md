# Binance Balanced Buying Bot (binance_bbb) 

A Roll-Your-Own approach to setting up your own customized Binance index fund to buy into using a dollar-cost-averaging investing philosophy.

Set up a customized basket of target cryptos and relative weights. Then the `binance_bbb` will buy each of them for you at the specified ratios.


# Setup
- Requires Python 3
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
```

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


# Testing your portfolio

## Minimum notional values
Binance specifies a minimum buy order value for each crypto (aka `minNotional`). Let's say you're looking to buy equal amounts of 10 different cryptos and only want to spend 0.005 BTC altogether. Obviously each order's notional value will then be 0.0005 BTC.

But the `minNotional` for BTC orders is 0.001; Binance will not let you place an order whose value is smaller than that.
