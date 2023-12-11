import random

from config import ETH_PRICE, TOKENS_PER_CHAIN
from modules import Logger, Aggregator
from settings import GLOBAL_NETWORK, OKX_BALANCE_WANTED, AMOUNT_PERCENT
from utils.tools import helper, gas_checker


class Custom(Logger, Aggregator):
    def __init__(self, client):
        Logger.__init__(self)
        Aggregator.__init__(self, client)

    async def swap(self):
        pass

    async def collect_eth_util(self):
        from functions import swap_odos, swap_oneinch, swap_openocean, swap_xyfinance, swap_rango, swap_avnu

        self.logger_msg(*self.client.acc_info, msg=f"Stark collecting tokens to ETH")

        func = {
            3: [swap_odos, swap_oneinch, swap_openocean, swap_xyfinance],
            4: [swap_rango, swap_openocean, swap_xyfinance],
            8: [swap_openocean, swap_xyfinance],
            9: [swap_avnu],
            11: [swap_openocean, swap_xyfinance, swap_odos, swap_oneinch]
        }[GLOBAL_NETWORK]

        wallet_balance = {k: await self.client.get_token_balance(k, False)
                          for k, v in TOKENS_PER_CHAIN[self.client.network.name].items()}
        valid_wallet_balance = {k: v[1] for k, v in wallet_balance.items() if v[0] != 0}
        eth_price = ETH_PRICE

        if 'ETH' in valid_wallet_balance:
            valid_wallet_balance['ETH'] = valid_wallet_balance['ETH'] * eth_price

        if len(valid_wallet_balance.values()) > 1:

            for token_name, token_balance in valid_wallet_balance.items():
                if token_name != 'ETH':
                    amount_in_wei = wallet_balance[token_name][0]
                    amount = float(f"{(amount_in_wei / 10 ** await self.client.get_decimals(token_name)):.6f}")
                    amount_in_usd = valid_wallet_balance[token_name]
                    if amount_in_usd > 1:
                        from_token_name, to_token_name = token_name, 'ETH'
                        data = from_token_name, to_token_name, amount, amount_in_wei
                        counter = 0
                        while True:
                            result = False
                            module_func = random.choice(func)
                            try:
                                self.logger_msg(*self.client.acc_info, msg=f'Launching swap module', type_msg='warning')
                                result = await module_func(self.client.account_name, self.client.private_key,
                                                           self.client.network, self.client.proxy_init, swapdata=data)
                            except:
                                counter += 1
                                pass
                            if result or counter == 3:
                                break
                    else:
                        self.logger_msg(*self.client.acc_info, msg=f"{token_name} balance < 1$")

            return True
        else:
            raise RuntimeError('Account balance already in ETH!')

    @helper
    @gas_checker
    async def collect_eth(self):
        await self.collect_eth_util()

    @helper
    @gas_checker
    async def balance_average(self):
        from functions import okx_withdraw

        self.logger_msg(*self.client.acc_info, msg=f"Stark check all balance to make average")

        amount = OKX_BALANCE_WANTED
        wanted_amount_in_usd = float(f'{amount * ETH_PRICE:.2f}')

        wallet_balance = {k: await self.client.get_token_balance(k, False)
                          for k, v in TOKENS_PER_CHAIN[self.client.network.name].items()}
        valid_wallet_balance = {k: v[1] for k, v in wallet_balance.items() if v[0] != 0}
        eth_price = ETH_PRICE

        if 'ETH' in valid_wallet_balance:
            valid_wallet_balance['ETH'] = valid_wallet_balance['ETH'] * eth_price

        valid_wallet_balance = {k: round(v, 7) for k, v in valid_wallet_balance.items()}

        sum_balance_in_usd = sum(valid_wallet_balance.values())

        if wanted_amount_in_usd > sum_balance_in_usd:
            need_to_withdraw = float(f"{(wanted_amount_in_usd - sum_balance_in_usd) / eth_price:.6f}")

            self.logger_msg(*self.client.acc_info, msg=f"Not enough balance on account, start OKX withdraw module")

            return await okx_withdraw(self.client.account_name, self.client.private_key, self.client.network,
                                      self.client.proxy_init, want_balance=need_to_withdraw)
        raise RuntimeError('Account has enough tokens on balance!')

    @helper
    @gas_checker
    async def wraps_abuser(self):
        from functions import swap_odos, swap_oneinch, swap_openocean, swap_xyfinance, swap_avnu

        func = {
            3: [swap_odos, swap_oneinch, swap_openocean, swap_xyfinance],
            4: [swap_openocean, swap_xyfinance],
            8: [swap_openocean, swap_xyfinance],
            9: [swap_avnu],
            11: [swap_odos, swap_oneinch, swap_openocean, swap_xyfinance]
        }[GLOBAL_NETWORK]

        current_tokens = list(TOKENS_PER_CHAIN[self.client.network.name].items())[:2]

        wallet_balance = {k: await self.client.get_token_balance(k, False) for k, v in current_tokens}
        valid_wallet_balance = {k: v[1] for k, v in wallet_balance.items() if v[0] != 0}
        eth_price = ETH_PRICE

        if 'ETH' in valid_wallet_balance:
            valid_wallet_balance['ETH'] = valid_wallet_balance['ETH'] * eth_price

        if 'WETH' in valid_wallet_balance:
            valid_wallet_balance['WETH'] = valid_wallet_balance['WETH'] * eth_price
            valid_wallet_balance['ETH'] = 0

        max_token = max(valid_wallet_balance, key=lambda x: valid_wallet_balance[x])
        percent = round(random.uniform(*AMOUNT_PERCENT)) / 100 if max_token == 'ETH' else 1
        amount_in_wei = int(wallet_balance[max_token][0] * percent)
        amount = float(f"{amount_in_wei / 10 ** 18:.6f}")

        if max_token == 'ETH':
            msg = f'Wrap {amount:.6f} ETH'
            from_token_name, to_token_name = 'ETH', 'WETH'
        else:
            msg = f'Unwrap {amount:.6f} WETH'
            from_token_name, to_token_name = 'WETH', 'ETH'

        self.logger_msg(*self.client.acc_info, msg=msg)

        if (max_token == 'ETH' and valid_wallet_balance[max_token] > 1
                or max_token == 'WETH' and valid_wallet_balance[max_token] != 0):
            data = from_token_name, to_token_name, amount, amount_in_wei
            counter = 0
            result = False
            while True:
                module_func = random.choice(func)
                try:
                    result = await module_func(self.client.account_name, self.client.private_key,
                                               self.client.network, self.client.proxy_init, swapdata=data)

                except:
                    pass
                if result or counter == 3:
                    break

            return result
        else:
            self.logger_msg(*self.client.acc_info, msg=f"{from_token_name} balance is too low (lower 1$)")