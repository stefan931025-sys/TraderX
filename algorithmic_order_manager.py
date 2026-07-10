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
        self.market_volatility = 0.15 
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
            logging.warning(f"Execution Halted: No active execution policy loaded.")
            return None

        # QUANT RISK GUARDRAIL
        base_max_allowed = self.active_policy.get("max_order_size", 10000)
        risk_factor = (0.20 / self.market_volatility) if self.market_volatility > 0.20 else 1.0
        dynamic_max_allowed = int(base_max_allowed * risk_factor)

        if quantity > dynamic_max_allowed:
            telemetry = {
                "order_id": order_id,
                "status": "REJECTED_BY_RISK",
                "market_volatility": f"{self.market_volatility * 100:.1f}%",
                "reason": f"Quantity ({quantity}) exceeds risk-adjusted limit of {dynamic_max_allowed}."
            }
            logging.warning(f"RISK TELEMETRY TRACE: {json.dumps(telemetry)}")
            return telemetry

        target_venue = self.active_policy["routing_logic"].get(side.upper(), "DARK_POOL")
        symbol = symbol.upper()
        
        if symbol not in self.portfolio:
            self.portfolio[symbol] = {"total_quantity": 0, "avg_price": 0.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0}
            
        is_buy = side.upper() == "BUY"
        current_qty = self.portfolio[symbol]["total_quantity"]
        current_avg = self.portfolio[symbol]["avg_price"]

        realized_gain = ((market_price - current_avg) * quantity) if (not is_buy and current_qty >= quantity) else 0.0
        new_qty = (current_qty + quantity) if is_buy else (current_qty - quantity)
        
        new_avg = round(((current_qty * current_avg) + (quantity * market_price)) / new_qty, 2) if (is_buy and new_qty > 0) else current_avg
        new_avg = 0.0 if new_qty == 0 else new_avg

        self.portfolio[symbol]["total_quantity"] = new_qty
        self.portfolio[symbol]["avg_price"] = new_avg
        self.portfolio[symbol]["realized_pnl"] += round(realized_gain, 2)
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

    def execute_twap_order(self, symbol, side, total_quantity, time_slices, simulated_prices):
        """
        TWAP EXECUTION ENGINE:
        Breaks down a massive parent block order into uniform child execution slices 
        to mitigate market footprint and tracking error.
        """
        logging.info(f"\n=======================================================")
        logging.info(f"INITIATING TWAP ALGORITHMIC LAYER: {side} {total_quantity} shares of {symbol.upper()}")
        logging.info(f"Slicing Strategy: {time_slices} intervals | Price Array Feed Active")
        logging.info(f"=======================================================\n")
        
        # Calculate individual slice size
        slice_qty = math.floor(total_quantity / time_slices)
        remaining_qty = total_quantity % time_slices
        
        for i in range(time_slices):
            slice_id = f"TWAP-CHILD-{uuid.uuid4().hex[:6].upper()}"
            current_market_price = simulated_prices[i] if i < len(simulated_prices) else simulated_prices[-1]
            
            # Append left-over odd lots to the final slice execution lot
            current_slice_qty = slice_qty + remaining_qty if (i == time_slices - 1) else slice_qty
            
            logging.info(f">> [INTERVAL {i+1}/{time_slices}] Routing Child Slice...")
            self.process_order(slice_id, symbol, side, current_slice_qty, current_market_price)
            
            # Simulated matching engine latency spacing
            time.sleep(0.1)

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

    # Simulated market price feed shifting upward during execution window
    market_price_evolution = [180.00, 180.50, 181.25, 182.00]
    
    # Execute an institutional order of 40,000 shares across 4 intervals
    manager.execute_twap_order("AAPL", "BUY", 40000, 4, market_price_evolution)
