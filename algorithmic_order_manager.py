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
        # Simulated market volatility index (e.g., annualized standard deviation of returns)
        # 0.15 = 15% (Quiet market), 0.45 = 45% (High volatility/Panic)
        self.market_volatility = 0.15 

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
        
        # Sizing Penalty Formula: Scales down order size if volatility exceeds 20% baseline
        if self.market_volatility > 0.20:
            risk_factor = 0.20 / self.market_volatility
            dynamic_max_allowed = int(base_max_allowed * risk_factor)
        else:
            dynamic_max_allowed = base_max_allowed

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

        telemetry = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "executed_quantity": quantity,
            "execution_price": market_price,
            "assigned_venue": target_venue,
            "status": "FILLED",
            "market_volatility": f"{self.market_volatility * 100:.1f}%",
            "policy_applied": self.active_policy["policy_name"],
            "explainability_notes": f"Vol-adjusted cap was {dynamic_max_allowed}. Route assigned via DSL ruleset."
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

    print("\n=== SCENARIO 1: NORMAL VOLATILITY (15%) ===")
    manager.update_market_conditions(0.15)
    manager.process_order("ORD-003", "AAPL", "BUY", 30000, 180.25)

    print("\n=== SCENARIO 2: MARKET TURMOIL / VOLATILITY SPIKE (45%) ===")
    manager.update_market_conditions(0.45)
    manager.process_order("ORD-004", "AAPL", "BUY", 30000, 178.50)
