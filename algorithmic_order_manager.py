import json
import time
import uuid
import logging
import math
import random

# Configure basic logging for telemetry tracing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlgorithmicOrderManager:
    def __init__(self):
        self.active_policy = None
        self.active_policy_version = None
        self.order_book = {}
        self.market_volatility = 0.15 
        self.portfolio = {}
        # Transaction fee structure: 5 basis points (0.0005) per execution
        self.bps_fee_rate = 0.0005 

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
        
        # --- MARKET SLIPPAGE & TRANSACTION COST SIMULATION ---
        # Large quantities push prices away from us. Volatility amplifies the slippage impact.
        slippage_factor = (quantity / dynamic_max_allowed) * self.market_volatility * 0.02
        
        # FIXED: BUY orders push execution price UP (+); SELL orders push execution price DOWN (-)
        if side.upper() == "BUY":
            effective_price = market_price * (1.0 + slippage_factor)
        else:
            effective_price = market_price * (1.0 - slippage_factor)
            
        # Calculate exchange commission (bps fee)
        notional_value = quantity * effective_price
        transaction_fee = notional_value * self.bps_fee_rate
        
        if symbol not in self.portfolio:
            self.portfolio[symbol] = {"total_quantity": 0, "avg_price": 0.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0, "total_fees_paid": 0.0}
            
        is_buy = side.upper() == "BUY"
        current_qty = self.portfolio[symbol]["total_quantity"]
        current_avg = self.portfolio[symbol]["avg_price"]

        realized_gain = ((effective_price - current_avg) * quantity) if (not is_buy and current_qty >= quantity) else 0.0
        
        if is_buy:
            new_qty = current_qty + quantity
            new_avg = round(((current_qty * current_avg) + (quantity * effective_price)) / new_qty, 2) if new_qty > 0 else 0.0
        else:
            new_qty = current_qty - quantity
            new_avg = current_avg if new_qty > 0 else 0.0

        self.portfolio[symbol]["total_quantity"] = new_qty
        self.portfolio[symbol]["avg_price"] = new_avg
        self.portfolio[symbol]["realized_pnl"] += round(realized_gain, 2)
        self.portfolio[symbol]["unrealized_pnl"] = round((effective_price - new_avg) * new_qty, 2) if new_qty > 0 else 0.0
        self.portfolio[symbol]["total_fees_paid"] += round(transaction_fee, 2)

        telemetry = {
            "order_id": order_id, "symbol": symbol, "side": side, "requested_qty": quantity,
            "mid_market_price": market_price, "effective_fill_price": round(effective_price, 2),
            "slippage_cost": round(abs(effective_price - market_price) * quantity, 2),
            "commission_fee": round(transaction_fee, 2), "assigned_venue": target_venue, "status": "FILLED",
            "position_state": {
                "current_inventory": self.portfolio[symbol]["total_quantity"],
                "avg_cost_basis": self.portfolio[symbol]["avg_price"]
            }
        }
        logging.info(f"COMPLIANCE TELEMETRY TRACE: {json.dumps(telemetry)}")
        return telemetry

    def calculate_and_rebalance(self, target_weights, current_prices, drift_threshold=0.02):
        logging.info("\n=======================================================")
        logging.info(f"RUNNING PORTFOLIO REBALANCING ENGINE (Threshold: {drift_threshold * 100:.1f}%)")
        logging.info("=======================================================")
        
        total_value = 0.0
        for symbol, price in current_prices.items():
            qty = self.portfolio.get(symbol, {}).get("total_quantity", 0)
            total_value += (qty * price)
            
        logging.info(f"Current Portfolio Mark-to-Market Total Value: ${total_value:,.2f}")
        
        for symbol, target_weight in target_weights.items():
            symbol = symbol.upper()
            price = current_prices[symbol]
            current_qty = self.portfolio.get(symbol, {}).get("total_quantity", 0)
            
            current_asset_value = current_qty * price
            current_weight = current_asset_value / total_value if total_value > 0 else 0.0
            
            target_value_for_asset = total_value * target_weight
            target_qty = int(target_value_for_asset / price)
            actual_drift = abs(current_weight - target_weight)
            
            logging.info(f"Checking {symbol} -> Target: {target_weight*100:.1f}% | Current: {current_weight*100:.1f}% | Drift: {actual_drift*100:.1f}%")
            
            if actual_drift <= drift_threshold:
                logging.info(f"   [GUARDRAIL HOLD] {symbol} drift is within tolerance. Execution suppressed.")
                continue
                
            qty_variance = target_qty - current_qty
            if qty_variance == 0:
                continue
                
            side = "BUY" if qty_variance > 0 else "SELL"
            trade_qty = abs(qty_variance)
            
            logging.info(f"   [TRIGGERED] Drift exceeds threshold! Generating {side} order for {trade_qty} shares.")
            rebalance_id = f"REBAL-{uuid.uuid4().hex[:6].upper()}"
            self.process_order(rebalance_id, symbol, side, trade_qty, price)

if __name__ == "__main__":
    manager = AlgorithmicOrderManager()

    v2_policy_dsl = """{
        "policy_name": "High-Volume Institutional Venue Routing Policy",
        "version": "2.5.0",
        "max_order_size": 50000,
        "routing_logic": { "BUY": "INTERNAL_DARK_POOL", "SELL": "PRIMARY_LIT_MARKET" }
    }"""
    manager.load_policy_dsl(v2_policy_dsl)

    # 1. Establish initial portfolio positions
    print("\n--- Establishing Initial Positions ---")
    manager.process_order("INIT-001", "AAPL", "BUY", 2000, 190.00)
    manager.process_order("INIT-002", "NVDA", "BUY", 3000, 85.00)

    # 2. Simulate a major market divergence causing real asset drift
    major_market_prices = {
        "AAPL": 150.00, 
        "NVDA": 140.00  
    }
    strategic_target_weights = {
        "AAPL": 0.60,
        "NVDA": 0.40
    }
    
    # Run engine
    manager.calculate_and_rebalance(strategic_target_weights, major_market_prices, drift_threshold=0.03)
