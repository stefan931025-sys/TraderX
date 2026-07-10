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

        base_max_allowed = self.active_policy.get("max_order_size", 10000)
        risk_factor = (0.20 / self.market_volatility) if self.market_volatility > 0.20 else 1.0
        dynamic_max_allowed = int(base_max_allowed * risk_factor)

        if quantity > dynamic_max_allowed:
            telemetry = {
                "order_id": order_id,
                "status": "REJECTED_BY_RISK",
                "reason": f"Quantity ({quantity}) exceeds limit of {dynamic_max_allowed}."
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
        
        if is_buy:
            new_qty = current_qty + quantity
            new_avg = round(((current_qty * current_avg) + (quantity * market_price)) / new_qty, 2) if new_qty > 0 else 0.0
        else:
            new_qty = current_qty - quantity
            new_avg = current_avg if new_qty > 0 else 0.0

        self.portfolio[symbol]["total_quantity"] = new_qty
        self.portfolio[symbol]["avg_price"] = new_avg
        self.portfolio[symbol]["realized_pnl"] += round(realized_gain, 2)
        self.portfolio[symbol]["unrealized_pnl"] = round((market_price - new_avg) * new_qty, 2) if new_qty > 0 else 0.0

        telemetry = {
            "order_id": order_id, "symbol": symbol, "side": side, "executed_quantity": quantity,
            "execution_price": market_price, "assigned_venue": target_venue, "status": "FILLED",
            "position_state": {
                "current_inventory": self.portfolio[symbol]["total_quantity"],
                "avg_cost_basis": self.portfolio[symbol]["avg_price"]
            }
        }
        logging.info(f"COMPLIANCE TELEMETRY TRACE: {json.dumps(telemetry)}")
        return telemetry

    def execute_twap_order(self, symbol, side, total_quantity, time_slices, simulated_prices):
        slice_qty = math.floor(total_quantity / time_slices)
        remaining_qty = total_quantity % time_slices
        
        for i in range(time_slices):
            slice_id = f"TWAP-CHILD-{uuid.uuid4().hex[:6].upper()}"
            current_market_price = simulated_prices[i] if i < len(simulated_prices) else simulated_prices[-1]
            current_slice_qty = slice_qty + remaining_qty if (i == time_slices - 1) else slice_qty
            self.process_order(slice_id, symbol, side, current_slice_qty, current_market_price)
            time.sleep(0.05)

    def calculate_and_rebalance(self, target_weights, current_prices):
        """
        PORTFOLIO REBALANCING ENGINE:
        Computes total Assets Under Management (AUM), checks weight deviations,
        and generates optimizing trades to restore target allocations.
        """
        logging.info("\n=======================================================")
        logging.info("RUNNING PORTFOLIO REBALANCING ENGINE")
        logging.info("=======================================================")
        
        # 1. Calculate current total portfolio value (Cash + Assets marked to market)
        total_value = 0.0
        for symbol, price in current_prices.items():
            qty = self.portfolio.get(symbol, {}).get("total_quantity", 0)
            total_value += (qty * price)
            
        logging.info(f"Current Portfolio Mark-to-Market Total Value: ${total_value:,.2f}")
        
        # 2. Determine target allocations vs current holdings
        for symbol, target_weight in target_weights.items():
            symbol = symbol.upper()
            price = current_prices[symbol]
            current_qty = self.portfolio.get(symbol, {}).get("total_quantity", 0)
            
            # Calculate what we should hold versus what we currently hold
            target_value_for_asset = total_value * target_weight
            target_qty = int(target_value_for_asset / price)
            qty_variance = target_qty - current_qty
            
            if qty_variance == 0:
                logging.info(f"Asset {symbol} is perfectly balanced at target weight ({target_weight*100}%).")
                continue
                
            side = "BUY" if qty_variance > 0 else "SELL"
            trade_qty = abs(qty_variance)
            
            logging.info(f">> Rebalance Signal for {symbol}: Current Qty={current_qty}, Target Qty={target_qty} | Generating {side} for {trade_qty} shares.")
            
            # Route rebalance instruction to execution engine
            rebalance_id = f"REBAL-{uuid.uuid4().hex[:6].upper()}"
            self.process_order(rebalance_id, symbol, side, trade_qty, price)

if __name__ == "__main__":
    manager = AlgorithmicOrderManager()

    v2_policy_dsl = """{
        "policy_name": "High-Volume Institutional Venue Routing Policy",
        "version": "2.0.0",
        "max_order_size": 100000,
        "routing_logic": { "BUY": "INTERNAL_DARK_POOL", "SELL": "PRIMARY_LIT_MARKET" }
    }"""
    manager.load_policy_dsl(v2_policy_dsl)

    # Setup initial uneven positions
    print("\n--- Establishing Initial Portfolio Positions ---")
    manager.process_order("INIT-001", "AAPL", "BUY", 1000, 180.00)
    manager.process_order("INIT-002", "NVDA", "BUY", 5000, 50.00)

    # Market shift occurs! Prices update.
    current_market_prices = {
        "AAPL": 190.00,
        "NVDA": 85.00
    }

    # Define target strategic allocation: 60% Apple, 40% Nvidia
    strategic_target_weights = {
        "AAPL": 0.60,
        "NVDA": 0.40
    }

    # Trigger structural rebalance
    manager.calculate_and_rebalance(strategic_target_weights, current_market_prices)
