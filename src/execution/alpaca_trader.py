"""
Alpaca Autonomous Trading API Client & Order Execution Module
============================================================

Handles real-time communication with Alpaca Paper Trading API:
- Account status and portfolio equity queries
- Open position tracking (equities and options)
- Autonomous options order execution (Protective Put submission)
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("alpaca_trader")

# Alpaca Trading SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        GetOrdersRequest,
    )
    from alpaca.trading.enums import (
        OrderSide,
        TimeInForce,
        OrderType,
        OrderStatus,
        AssetClass,
    )
    ALPACA_TRADING_AVAILABLE = True
except ImportError:
    ALPACA_TRADING_AVAILABLE = False
    logger.warning("alpaca-py trading module not available, running in simulated execution mode.")


class AlpacaTrader:
    """Autonomous execution client for Alpaca paper and live environments."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        paper: bool = True
    ):
        self.api_key = api_key or os.getenv("APCA_API_KEY_ID") or os.getenv("APCA_API_KEY")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY") or os.getenv("APCA_API_SECRET")
        self.base_url = base_url or os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets/v2")
        self.paper = paper

        self.client: Optional[TradingClient] = None

        if ALPACA_TRADING_AVAILABLE and self.api_key and self.secret_key:
            try:
                self.client = TradingClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                    paper=self.paper
                )
                logger.info("Initialized Alpaca TradingClient successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca TradingClient: {e}. Falling back to simulation mode.")
                self.client = None
        else:
            logger.info("Running in autonomous simulated trading mode.")

    def get_account_status(self) -> Dict[str, Any]:
        """Fetch current account equity, cash, and buying power."""
        if self.client:
            try:
                acct = self.client.get_account()
                return {
                    "account_id": str(acct.id),
                    "status": str(acct.status),
                    "currency": acct.currency,
                    "equity": float(acct.equity),
                    "cash": float(acct.cash),
                    "buying_power": float(acct.buying_power),
                    "portfolio_value": float(acct.portfolio_value),
                    "initial_margin": float(acct.initial_margin) if hasattr(acct, "initial_margin") else 0.0,
                    "maintenance_margin": float(acct.maintenance_margin) if hasattr(acct, "maintenance_margin") else 0.0,
                    "last_equity": float(acct.last_equity) if hasattr(acct, "last_equity") else float(acct.equity),
                    "is_live_connection": True
                }
            except Exception as e:
                logger.error(f"Error querying Alpaca account: {e}. Returning simulated $100k account.")

        # Default fallback account state ($100,000 hackathon starting balance)
        return {
            "account_id": "SIMULATED_HACKATHON_PAPER_ACCOUNT",
            "status": "ACTIVE",
            "currency": "USD",
            "equity": 100000.0,
            "cash": 100000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "initial_margin": 0.0,
            "maintenance_margin": 0.0,
            "last_equity": 100000.0,
            "is_live_connection": False
        }

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open equity and option positions."""
        if self.client:
            try:
                positions = self.client.get_all_positions()
                return [
                    {
                        "symbol": pos.symbol,
                        "qty": float(pos.qty),
                        "market_value": float(pos.market_value),
                        "current_price": float(pos.current_price),
                        "avg_entry_price": float(pos.avg_entry_price),
                        "unrealized_pl": float(pos.unrealized_pl),
                        "unrealized_plpc": float(pos.unrealized_plpc),
                        "asset_class": str(pos.asset_class),
                        "side": str(pos.side)
                    }
                    for pos in positions
                ]
            except Exception as e:
                logger.error(f"Error fetching open positions: {e}")
        return []

    def execute_options_hedge(
        self,
        option_symbol: str,
        contract_qty: int,
        side: str = "buy",
        order_type: str = "market",
        limit_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Autonomously executes a protective put option trade on Alpaca.

        Args:
            option_symbol: Standard OCC option contract (e.g. SPY260918P00550000).
            contract_qty: Number of contracts to purchase.
            side: Order side ('buy' for protective put).
            order_type: 'market' or 'limit'.
            limit_price: Optional limit price per share.
            time_in_force: 'day' or 'gtc'.

        Returns:
            Structured order execution confirmation dictionary.
        """
        logger.info(f"Submitting {side.upper()} order for {contract_qty}x {option_symbol} (type={order_type})...")

        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif = TimeInForce.DAY if time_in_force.lower() == "day" else TimeInForce.GTC

        if self.client:
            try:
                if order_type.lower() == "limit" and limit_price is not None:
                    req = LimitOrderRequest(
                        symbol=option_symbol,
                        qty=contract_qty,
                        side=order_side,
                        time_in_force=tif,
                        limit_price=round(limit_price, 2)
                    )
                else:
                    req = MarketOrderRequest(
                        symbol=option_symbol,
                        qty=contract_qty,
                        side=order_side,
                        time_in_force=tif
                    )

                submitted_order = self.client.submit_order(req)

                result = {
                    "status": "SUBMITTED",
                    "order_id": str(submitted_order.id),
                    "client_order_id": str(submitted_order.client_order_id),
                    "symbol": submitted_order.symbol,
                    "qty": float(submitted_order.qty),
                    "order_type": str(submitted_order.order_type),
                    "side": str(submitted_order.side),
                    "time_in_force": str(submitted_order.time_in_force),
                    "filled_avg_price": float(submitted_order.filled_avg_price) if submitted_order.filled_avg_price else limit_price,
                    "alpaca_order_status": str(submitted_order.status),
                    "submitted_at": submitted_order.submitted_at.isoformat() if submitted_order.submitted_at else datetime.now(timezone.utc).isoformat(),
                    "is_simulated": False
                }
                logger.info(f"Order {submitted_order.id} submitted successfully to Alpaca.")
                return result
            except Exception as e:
                logger.error(f"Live Alpaca order submission failed: {e}. Executing in high-fidelity simulated paper mode.")

        # High-Fidelity Paper Trading Simulation
        sim_order_id = f"SIM-ORD-{int(datetime.now(timezone.utc).timestamp())}"
        est_price = limit_price if limit_price is not None else 3.50
        result = {
            "status": "FILLED_SIMULATED",
            "order_id": sim_order_id,
            "client_order_id": f"CLIENT-{sim_order_id}",
            "symbol": option_symbol,
            "qty": contract_qty,
            "order_type": order_type.upper(),
            "side": side.upper(),
            "time_in_force": time_in_force.upper(),
            "filled_avg_price": est_price,
            "total_notional_cost": round(contract_qty * est_price * 100.0, 2),
            "alpaca_order_status": "filled",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
            "message": f"Autonomous protective put simulated fill: {contract_qty}x {option_symbol} @ ${est_price:.2f}."
        }
        logger.info(f"Simulated order filled: {result['message']}")
        return result
