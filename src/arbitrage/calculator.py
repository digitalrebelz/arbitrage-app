"""Arbitrage profit calculator."""

from decimal import Decimal

from src.models.market import Orderbook, Ticker


class ArbitrageCalculator:
    """Calculate arbitrage profits with fees and slippage."""

    @staticmethod
    def calculate_cross_exchange_profit(
        buy_ticker: Ticker,
        sell_ticker: Ticker,
        buy_fee_percent: Decimal,
        sell_fee_percent: Decimal,
        transfer_fee: Decimal = Decimal("0"),
        volume: Decimal = Decimal("1"),
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate profit for cross-exchange arbitrage.

        Args:
            buy_ticker: Ticker from buy exchange (using ask price)
            sell_ticker: Ticker from sell exchange (using bid price)
            buy_fee_percent: Fee on buy exchange (%)
            sell_fee_percent: Fee on sell exchange (%)
            transfer_fee: Fixed transfer/withdrawal fee
            volume: Trade volume

        Returns:
            Tuple of (gross_profit_percent, net_profit_percent, profit_usd)
        """
        buy_price = buy_ticker.ask
        sell_price = sell_ticker.bid

        if buy_price == 0 or sell_price == 0:
            return Decimal("0"), Decimal("0"), Decimal("0")

        # Gross profit (before fees)
        gross_profit_percent = ((sell_price - buy_price) / buy_price) * 100

        # Total fees
        total_fee_percent = buy_fee_percent + sell_fee_percent

        # Net profit after fees
        net_profit_percent = gross_profit_percent - total_fee_percent

        # Calculate actual USD profit
        buy_cost = volume * buy_price * (1 + buy_fee_percent / 100)
        sell_revenue = volume * sell_price * (1 - sell_fee_percent / 100)
        profit_usd = sell_revenue - buy_cost - transfer_fee

        return gross_profit_percent, net_profit_percent, profit_usd

    @staticmethod
    def calculate_max_executable_volume(
        buy_orderbook: Orderbook,
        sell_orderbook: Orderbook,
        min_profit_percent: Decimal,
        buy_fee_percent: Decimal,
        sell_fee_percent: Decimal,
    ) -> Decimal:
        """
        Calculate maximum volume that can be executed profitably.

        Walks through both orderbooks to find the maximum volume
        where the spread still exceeds fees + minimum profit.

        Args:
            buy_orderbook: Orderbook to buy from (using asks)
            sell_orderbook: Orderbook to sell into (using bids)
            min_profit_percent: Minimum required profit (%)
            buy_fee_percent: Buy exchange fee (%)
            sell_fee_percent: Sell exchange fee (%)

        Returns:
            Maximum executable volume
        """
        total_fee_percent = buy_fee_percent + sell_fee_percent
        required_spread = total_fee_percent + min_profit_percent

        max_volume = Decimal("0")
        buy_filled = Decimal("0")
        sell_filled = Decimal("0")
        buy_idx = 0
        sell_idx = 0

        while buy_idx < len(buy_orderbook.asks) and sell_idx < len(sell_orderbook.bids):
            buy_level = buy_orderbook.asks[buy_idx]
            sell_level = sell_orderbook.bids[sell_idx]

            # Calculate spread at these levels
            spread_percent = ((sell_level.price - buy_level.price) / buy_level.price) * 100

            if spread_percent < required_spread:
                break

            # Calculate volume available at both levels
            buy_available = buy_level.volume - buy_filled
            sell_available = sell_level.volume - sell_filled
            trade_volume = min(buy_available, sell_available)
            max_volume += trade_volume

            # Move to next level if current is exhausted
            if buy_available <= sell_available:
                buy_idx += 1
                buy_filled = Decimal("0")
                sell_filled += trade_volume
            else:
                sell_idx += 1
                sell_filled = Decimal("0")
                buy_filled += trade_volume

        return max_volume

    @staticmethod
    def estimate_slippage(
        orderbook: Orderbook,
        side: str,
        volume: Decimal,
    ) -> Decimal:
        """
        Estimate slippage for a given volume.

        Args:
            orderbook: Orderbook to execute against
            side: "buy" (hit asks) or "sell" (hit bids)
            volume: Volume to execute

        Returns:
            Estimated slippage as percentage
        """
        if volume == 0:
            return Decimal("0")

        avg_price, available_volume = orderbook.get_executable_price(side, volume)

        if available_volume == 0:
            return Decimal("100")  # No liquidity

        if available_volume < volume:
            return Decimal("50")  # Partial fill - high slippage

        # Get best price
        best_price = orderbook.best_bid if side == "sell" else orderbook.best_ask

        if best_price == 0:
            return Decimal("0")

        # Slippage is difference from best price
        slippage_percent = abs((avg_price - best_price) / best_price) * 100
        return slippage_percent

    @staticmethod
    def calculate_triangular_profit(
        price_ab: Decimal,
        price_bc: Decimal,
        price_ca: Decimal,
        fee_percent: Decimal,
    ) -> tuple[Decimal, bool]:
        """
        Calculate profit for triangular arbitrage.

        For path A -> B -> C -> A:
        - Buy B with A at price_ab
        - Buy C with B at price_bc
        - Buy A with C at price_ca

        Args:
            price_ab: Price of B in A (e.g., BTC/USD)
            price_bc: Price of C in B (e.g., ETH/BTC)
            price_ca: Price of A in C (e.g., USD/ETH)
            fee_percent: Fee per trade (%)

        Returns:
            Tuple of (profit_percent, is_forward_profitable)
        """
        if price_ab == 0 or price_bc == 0 or price_ca == 0:
            return Decimal("0"), False

        fee_multiplier = 1 - fee_percent / 100

        # Forward path: A -> B -> C -> A
        # Start with 1 unit of A
        # Buy B: 1 / price_ab * fee = amount of B
        # Buy C: B / price_bc * fee = amount of C
        # Buy A: C * price_ca * fee = amount of A
        forward_result = (
            (Decimal("1") / price_ab)
            * fee_multiplier
            * (Decimal("1") / price_bc)
            * fee_multiplier
            * price_ca
            * fee_multiplier
        )

        # Reverse path: A -> C -> B -> A
        reverse_result = (
            (Decimal("1") / price_ca)
            * fee_multiplier
            * price_bc
            * fee_multiplier
            * price_ab
            * fee_multiplier
        )

        forward_profit = (forward_result - 1) * 100
        reverse_profit = (reverse_result - 1) * 100

        if forward_profit > reverse_profit:
            return forward_profit, True
        return reverse_profit, False

    @staticmethod
    def calculate_effective_rate(
        rate: Decimal,
        fee_percent: Decimal,
        slippage_percent: Decimal,
    ) -> Decimal:
        """
        Calculate effective rate after fees and slippage.

        Args:
            rate: Base rate/profit (%)
            fee_percent: Total fees (%)
            slippage_percent: Estimated slippage (%)

        Returns:
            Effective rate after costs (%)
        """
        return rate - fee_percent - slippage_percent
