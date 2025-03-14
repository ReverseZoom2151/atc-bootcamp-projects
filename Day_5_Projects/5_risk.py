import ccxt
import time, schedule
import pandas as pd
import sys
import os

# Add parent directory to sys.path to allow imports across directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Day_4_Projects.key_file_2 import key as xP_KEY, secret as xP_SECRET

# Initialize Phemex client with required parameters
phemex = ccxt.phemex({
    'enableRateLimit': True,
    'apiKey': xP_KEY,
    'secret': xP_SECRET
})

def test_api_connection():
    """Test the API connection and return True if successful, False otherwise"""
    try:
        # Try a public endpoint that doesn't require authentication
        phemex.fetch_ticker('BTC/USD:BTC')
        print("Public API connection successful")
        
        # Now try a private endpoint
        try:
            bal = phemex.fetch_balance()
            print("✅ Private API authentication successful")
            return True
        except Exception as e:
            error_message = str(e)
            if "401 Request IP mismatch" in error_message:
                print("\n⚠️ ERROR: IP MISMATCH - Your current IP address is not authorized")
                print("You need to update your Phemex API key settings to allow your current IP address.")
                print("1. Login to Phemex")
                print("2. Go to 'Account & Security' -> 'API Management'")
                print("3. Edit your API key to add your current IP address\n")
            else:
                print(f"❌ Private API authentication failed: {e}")
            return False
    except Exception as e:
        print(f"❌ Public API connection failed: {e}")
        return False

symbol = 'BTC/USD:BTC'
size = 1
bid = 29000
params = {'timeInForce': 'PostOnly'}

def open_positions(symbol=symbol):
    if symbol == 'BTC/USD:BTC':
        index_pos = 4
    elif symbol == 'APE/USD:BTC':
        index_pos = 2
    elif symbol == 'ETH/USD:BTC':
        index_pos = 3
    elif symbol == 'DOGE/USD:BTC':
        index_pos = 1
    elif symbol == 'u100000SHIB/USD:BTC':
        index_pos = 0
    else:
        index_pos = None

    try:
        params = {'type': 'swap', 'code':'USD'}
        phe_bal = phemex.fetch_balance(params=params)
        open_positions = phe_bal['info']['data']['positions']

        openpos_side = open_positions[index_pos]['side']
        openpos_size = open_positions[index_pos]['size']

        if openpos_side == ('Buy'):
            openpos_bool = True
            long = True
        elif openpos_side == ('Sell'):
            openpos_bool = True
            long = False
        else:
            openpos_bool = False
            long = None
            
        print(f'open_positions... | openpos_bool {openpos_bool} | openpos_size {openpos_size} | long {long} | index_pos {index_pos}')

        return open_positions, openpos_bool, openpos_size, long, index_pos
    except Exception as e:
        print(f"Error in open_positions: {e}")
        return None, False, 0, None, index_pos

def ask_bid(symbol=symbol):
    try:
        ob = phemex.fetch_order_book(symbol)
        bid = ob['bids'][0][0]
        ask = ob['asks'][0][0]
        print(f'this is the ask for {symbol} {ask}')
        return ask, bid
    except Exception as e:
        print(f"Error fetching order book: {e}")
        return 0, 0

def kill_switch(symbol=symbol):
    
    print(f'starting the kill switch for {symbol}')
    
    try:
        position_info = open_positions(symbol)
        if position_info[0] is None:
            print("Failed to get position information. Exiting kill switch.")
            return
            
        openposi = position_info[1]
        long = position_info[3]
        kill_size = position_info[2]

        print(f'openposi {openposi} | long {long} | kill_size {kill_size}')

        while openposi == True:
            try:
                print('starting kill switch loop till limit fill...')
                temp_df = pd.DataFrame()
                print('just made a temp df')

                phemex.cancel_all_orders(symbol)
                position_info = open_positions(symbol)
                if position_info[0] is None:
                    print("Failed to get updated position information. Exiting kill switch.")
                    break
                    
                openposi = position_info[1]
                long = position_info[3]
                kill_size = position_info[2]
                kill_size = int(kill_size)
                
                price_info = ask_bid(symbol)
                if price_info[0] == 0:
                    print("Failed to get price information. Retrying in 30 seconds.")
                    time.sleep(30)
                    continue
                    
                ask, bid = price_info

                if long == False:
                    try:
                        phemex.create_limit_buy_order(symbol, kill_size, bid, params)
                        print(f'just made a BUY to CLOSE order of {kill_size} {symbol} at ${bid}')
                    except Exception as e:
                        print(f"Error placing buy order: {e}")
                    print('sleeping for 30 seconds to see if it fills...')
                    time.sleep(30)
                elif long == True:
                    try:
                        phemex.create_limit_sell_order(symbol, kill_size, ask, params)
                        print(f'just made a SELL to CLOSE order of {kill_size} {symbol} at ${ask}')
                    except Exception as e:
                        print(f"Error placing sell order: {e}")
                    print('sleeping for 30 seconds to see if it fills...')
                    time.sleep(30)
                else:
                    print('++++++ SOMETHING I DIDNT EXPECT HAPPENED IN KILL SWITCH ++++++')
                
                position_info = open_positions(symbol)
                if position_info[0] is None:
                    print("Failed to get updated position information. Exiting kill switch.")
                    break
                openposi = position_info[1]
            except Exception as e:
                print(f"Error in kill switch loop: {e}")
                print("Waiting 30 seconds before retrying...")
                time.sleep(30)
    except Exception as e:
        print(f"Error in kill_switch: {e}")

# Main execution
if __name__ == "__main__":
    print("\n=== Phemex Risk Management Tool ===\n")
    
    # Test API connection before proceeding
    if not test_api_connection():
        print("\nExiting program due to API connection issues.")
        sys.exit(1)
    
    # If we reach here, API connection was successful
    try:
        print("\nFetching balance information...")
        bal = phemex.fetch_balance()
        print("Balance information retrieved successfully")
        
        # Get position information
        print("\nChecking for open positions...")
        position_data = open_positions()
        
        if position_data[1]:  # If open position exists
            print(f"\nFound open position for {symbol}")
            print(f"Side: {'Long' if position_data[3] else 'Short'}")
            print(f"Size: {position_data[2]}")
            
            # Ask if user wants to close the position
            user_input = input("\nDo you want to close this position? (y/n): ")
            if user_input.lower() == 'y':
                print("\nInitiating kill switch to close position...")
                kill_switch()
            else:
                print("\nKeeping position open. Exiting program.")
        else:
            print("\nNo open positions found for the specified symbol.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your API key settings and try again.")
