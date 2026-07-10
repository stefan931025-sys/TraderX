import json
import time
import uuid
import logging
import math

# Configure basic logging for telemetry tracing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlgorithmicOrderManager:
    def __init__(self):
        self.active_policy = None
        self.active_policy_version = None
        self.order_book = {}
        # Simulated market volatility index (0.15 = 15% Quiet, 0.45 = 45% Panic)
        self.market_volatility = 0.15 
        
        # PORTFOLIO STATE TRACKER: Tracks inventory, cost basis, and realized profits
        self.portfolio = {}

    def update_market_conditions(self, new_volatility):
        """Simulates updating the live market volatility feed."""
        self.market_volatility = new_volatility
        logging.info(f"--- MARKET UPDATE: Volatility is now {new_volatility * 100:.1f}% ---")

    def load_policy_dsl(self, dsl_json_string):
        try:
            policy_data = json.loads(dsl_json_string)
            required_keys = ["policy_name", "version", "routing_logic", "max_order_size"]
            for key in required_keys:
                if key not in policy_data:
                    raise ValueError(f"Guardrail Alert: Missing required DSL parameter: '{key}'")
            
            old_version = self.active_policy_version
            self.active_policy = policy_data
            self.active_policy_version = policy_data["version"]
            
            logging.info(f"HOT-SWAP SUCCESSFUL: Upgraded policy from v({old_version}) to v({self.active_policy_version})")
            return True
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"HOT-SWAP REJECTED: Runtime guardrail caught invalid configuration. Error: {e}")
            return False

    def process_order(self, order_id, symbol, side, quantity, market_price):
        if not self.active_policy:
            logging.warning(f"Execution Halted: No active execution policy loaded to process order {order_id}.")
            return None

        # QUANT RISK GUARDRAIL: Calculate risk-adjusted maximum allowed order size
        base_max_allowed = self.active_policy.get("max_order_size", 10000)
        
        # MOBILE-SAFE QUANT FEED: Calculates factor inline to guarantee error-free execution
        risk_factor = (0.20 / self.market_volatility) if self.market_volatility > 0.20 else 1.0
        dynamic_max_allowed = int(base_max_allowed * risk_factor)

        if quantity > dynamic_max_allowed:
            telemetry = {
                "order_id": order_id,
                "status": "REJECTED_BY_RISK",
                "market_volatility": f"{self.market_volatility * 100:.1f}%",
                "base_limit": base_max_allowed,
                "risk_adjusted_limit": dynamic_max_allowed,
                "reason": f"Quantity ({quantity}) exceeds risk-adjusted limit of {dynamic_max_allowed} under current volatility."
            }
            logging.warning(f"RISK TELEMETRY TRACE: {json.dumps(telemetry)}")
            return telemetry

        # Determine venue route dynamically
        target_venue = self.active_policy["routing_logic"].get(side.upper(), "DARK_POOL")

        # Initialize asset track if not present
        symbol = symbol.upper()
        if symbol not in self.portfolio:
            self.portfolio[symbol] = {"total_quantity": 0, "avg_price": 0.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0}
            
        is_buy = side.upper() == "BUY"
        current_qty = self.portfolio[symbol]["total_quantity"]
        current_avg = self.portfolio[symbol]["avg_price"]

        # Calculate Realized PnL on Sells, or update Avg Price on Buys inline
        realized_gain = ((market_price - current_avg) * quantity) if (not is_buy and current_qty >= quantity) else 0.0
        new_qty = (current_qty + quantity) if is_buy else (current_qty - quantity)
        
        # Update average execution price strictly on accumulation (Buys)
        new_avg = round(((current_qty * current_avg) + (quantity * market_price)) / new_qty, 2) if (is_buy and new_qty > 0) else current_avg
        new_avg = 0.0 if new_qty == 0 else new_avg

        # Commit updates to state tracking ledger
        self.portfolio[symbol]["total_quantity"] = new_qty
        self.portfolio[symbol]["avg_price"] = new_avg
        self.portfolio[symbol]["realized_pnl"] += round(realized_gain, 2)
        
        # Mark-to-Market (MtM) Unrealized PnL Calculation
        self.portfolio[symbol]["unrealized_pnl"] = round((market_price - new_avg) * new_qty, 2) if new_qty > 0 else 0.0

        telemetry = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "executed_quantity": quantity,
            "execution_price": market_price,
            "assigned_venue": target_venue,
            "status": "FILLED",
            "position_state": {
                "current_inventory": self.portfolio[symbol]["total_quantity"],
                "avg_cost_basis": self.portfolio[symbol]["avg_price"],
                "unrealized_mtm_pnl": self.portfolio[symbol]["unrealized_pnl"],
                "realized_booked_pnl": self.portfolio[symbol]["realized_pnl"]
            }
        }

        logging.info(f"COMPLIANCE TELEMETRY TRACE: {json.dumps(telemetry, indent=2)}")
        return telemetry

if __name__ == "__main__":
    manager = AlgorithmicOrderManager()

    v2_policy_dsl = """{
        "policy_name": "High-Volume Institutional Venue Routing Policy",
        "version": "2.0.0",
        "max_order_size": 50000,
        "routing_logic": {
            "BUY": "INTERNAL_DARK_POOL",
            "SELL": "PRIMARY_LIT_MARKET"
        }
    }"""
    
    manager.load_policy_dsl(v2_policy_dsl)

    print("\n=== STAGE 1: ACCUMULATION ===")
    manager.process_order("ORD-003", "AAPL", "BUY", 10000, 180.00)
    manager.process_order("ORD-004", "AAPL", "BUY", 15000, 185.00)

    print("\n=== STAGE 2: MARKET RALLIES & WE SCALE OUT ===")
    # Market jumps to 195.00. We sell 10,000 shares to book a profit.
    manager.process_order("ORD-005", "AAPL", "SELL", 10000, 195.00)

    print("\n=== STAGE 3: VOLATILITY SHOCK intercepted ===")
    manager.update_market_conditions(0.45)
    manager.process_order("ORD-006", "AAPL", "BUY", 25000, 178.50)
