import os
import hjson as js
from pprint import pprint

class Transaction:
    def __init__(self, stock, timing: str, price, quantity):
        assert isinstance(timing, str)
        assert isinstance(price, int) or isinstance(price, float)
        assert isinstance(quantity, int)
        self.stock = stock
        self.timing = timing
        self.id = self.timing2id(timing)
        self.price = price
        self.quantity = quantity

    @staticmethod
    def timing2id(timing: str) -> int:
        tmp = timing.split('-')
        assert len(tmp) == 3
        tmp = [int(_) for _ in tmp]
        return tmp[0] * 10**6 + tmp[1] * 10**2 + tmp[2]

    @property
    def fee(self) -> float:
        return self.price * self.quantity

    @property
    def fee_final(self) -> float:
        return self.fee * (1 - self.service_percent)

    @property
    def service_percent(self):
        raise NotImplementedError

    @property
    def service_charge(self) -> float:
        return self.fee * self.service_percent

class BuyTransaction(Transaction):
    def __init__(self, stock, timing, price, quantity):
        super().__init__(stock, timing, price, quantity)
        self.empty = False
        self.sells = []

    def __str__(self) -> str:
        s = f'''
## {self.timing}

### Buy

{self.price} x {self.quantity}, {self.service_percent}
fee: {self.fee_final} = {self.fee} - {self.service_charge}

### Sell
'''
        for _ in self.sells:
            s += f'''
{_.price} x {_.quantity}, {_.service_percent}
fee: {_.fee_final} = {_.fee} - {_.service_charge}
'''
        return s

    @property
    def service_percent(self) -> float:
        ret = self.stock.commission + self.stock.transfer_fee
        return ret

    @property
    def quantity_left(self):
        delta = self.quantity
        for sell in self.sells:
            delta -= sell.quantity
        self.empty = delta == 0
        return delta

    def sell(self, tr):
        self.sells.append(tr)
        assert self.quantity_left >= 0, self.quantity_left

class SellTransaction(Transaction):
    def __init__(self, stock, timing, price, quantity) -> None:
        super().__init__(stock, timing, price, quantity)

    @property
    def service_percent(self):
        return self.stock.commission + self.stock.transfer_fee + self.stock.stamp_duty

class Stock:
    def __init__(self, name, id, commission=0.0005, stamp_duty=0.0005, transfer_fee=0.00001):
        self.id = id
        self.name = name
        self.commission = commission
        self.stamp_duty = stamp_duty
        self.transfer_fee = transfer_fee
        self._tr_recorder = {}
 
    def __str__(self) -> str:
        s = f'# {self.name} ({self.id})\n'
        for _, tr in self._tr_recorder.items():
            s += str(tr)
        return s

    def buy(self, timing, price, quantity):
        tr = BuyTransaction(self, timing, price, quantity)
        self._tr_recorder[tr.id] = tr

    def sell(self, buy_timing, timing, price, quantity):
        tr = SellTransaction(self, timing, price, quantity)
        trans_buy = self._tr_recorder[Transaction.timing2id(buy_timing)]
        trans_buy.sell(tr)

class StockManager:
    def __init__(self) -> None:
        self.stocks = {}

    def add_database(self, file: str):
        with open(file, 'r') as f:
            db = js.load(f)

            stock = Stock(
                name=db['name'],
                id=db['id'],
                commission=db['commission'],
                stamp_duty=db['stamp_duty'],
                transfer_fee=db['transfer_fee']
            )

            self.stocks[stock.name] = stock

            for buy in db['record']:
                stock.buy(
                    timing=buy['timing'],
                    price=buy['price'],
                    quantity=buy['quantity'],
                )
                for sell in buy['sell']:
                    stock.sell(
                        timing=sell['timing'],
                        buy_timing=buy['timing'],
                        price=sell['price'],
                        quantity=sell['quantity'],
                    )

    def output(self, dir: str):
        assert os.path.exists(dir)
        for name, stk in self.stocks.items():
            file = dir + f'/{name}.md'
            with open(file, 'w') as f:
                f.write(str(stk))


if __name__ == '__main__':
    stock = Stock('ABC', 30063, commission=0.0003, stamp_duty=0.0005, transfer_fee=0.00002)

    stock.buy('2024-0205-10', 25.6, 200)
    stock.sell('2024-0205-10', '2024-0312-14', 36.36, 200)

    stock.buy('2024-0206-10', 27.85, 200)
    stock.sell('2024-0206-10', '2024-0312-14', 36.36, 200)

    # print(stock)

    smgr = StockManager()
    smgr.add_database('tests/data.hjson')
    smgr.output('tests/result/')