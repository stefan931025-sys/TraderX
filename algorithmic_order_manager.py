import json
import time
import uuid
import logging

# Configure basic logging for telemetry tracing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlgorithmicOrderManager:
    def __init__(self):
        # Active execution policy storage (The DSL State)
        self.active_policy = None
        self.active_policy_version = None
        
        # Order Tracking Matrix
        self.order_book = {}

    def load_policy_dsl(self, dsl_json_string):
        """
        Requirement 1 & 2: Dynamic Policy Loading with Guardrails
        Parses the JSON-based DSL and checks constraints before swapping.
        """
        try:
            policy_data = json.loads(dsl_json_string)
            
            # Hot-swap Guardrail validation
            required_keys = ["policy_name", "version", "routing_logic", "max_order_size"]
            for key in required_keys:
                if key not in policy_data:
                    raise ValueError(f"Guardrail Alert: Missing required DSL structural parameters: '{key}'")
            
            # Commit the hot-swap seamlessly without restarting the application state
            old_version = self.active_policy_version
            self.active_policy = policy_data
            self.active_policy_version = policy_data["version"]
            
            logging.info(f"HOT-SWAP SUCCESSFUL: Upgraded policy from v{old_version} to v{self.active_policy_version} ({policy_data['policy_name']})")
            return True
            
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"HOT-SWAP REJECTED: Runtime guardrail caught invalid policy configuration. Error: {e}")
            return False

    def process_order(self, order_id, symbol, side, quantity, market_price):
        """
        Requirement 3: Execute Orders with Policy Outcome Telemetry & Explainability
        """
        if not self.active_policy:
            logging.warning(f"Execution Halted: No active execution policy loaded to process order {order_id}.")
            return None
            
        # Enforce max limit boundaries from the active runtime policy
        max_allowed = self.active_policy.get("max_order_size", 10000)
        if quantity > max_allowed:
            telemetry = {
                "order_id": order_id,
                "status": "REJECTED",
                "policy_version": self.active_policy_version,
                "reason": f"Quantity {quantity} exceeds strict policy limit boundary of {max_allowed}."
            }
            logging.warning(f"TELEMETRY TRACE: {json.dumps(telemetry)}")
            return telemetry

        # Determine execution venue route dynamically based on active DSL routing rules
        target_venue = self.active_policy["routing_logic"].get(side.upper(), "DARK_POOL")
        
        # Build out explainability fields
        telemetry = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "executed_quantity": quantity,
            "execution_price": market_price,
            "assigned_venue": target_venue,
            "status": "FILLED",
            "policy_applied": self.active_policy["policy_name"],
            "policy_version": self.active_policy_version,
            "explainability_notes": f"Route determined dynamically using criteria set by version {self.active_policy_version}. Side '{side}' mapped to venue '{target_venue}'."
        }
        
        logging.info(f"TELEMETRY TRACE: {json.dumps(telemetry, indent=2)}")
        return telemetry


# --- RUNTIME TEST EXECUTION SIMULATION ---
if __name__ == "__main__":
    manager = AlgorithmicOrderManager()
    
    # 1. Define Version 1.0.0 DSL Policy (Conservative Execution)
    v1_policy_dsl = """{
        "policy_name": "Conservative Retail Routing Policy",
        "version": "1.0.0",
        "max_order_size": 2000,
        "routing_logic": {
            "BUY": "RETAIL_EXCHANGE_A",
            "SELL": "RETAIL_EXCHANGE_B"
        }
    }"""
    
    # 2. Define Version 2.0.0 DSL Policy (Institutional High-Volume Hot-Swap Candidate)
    v2_policy_dsl = """{
        "policy_name": "High-Volume Institutional Venue Routing Policy",
        "version": "2.0.0",
        "max_order_size": 50000,
        "routing_logic": {
            "BUY": "INTERNAL_DARK_POOL",
            "SELL": "PRIMARY_LIT_MARKET"
        }
    }"""

    print("\n=== STEP 1: INITIALIZING ENGINE WITH V1 POLICY ===")
    manager.load_policy_dsl(v1_policy_dsl)
    
    print("\n=== STEP 2: PROCESSING ORDERS UNDER V1 RULES ===")
    # Standard order fitting constraints
    manager.process_order("ORD-001", "AAPL", "BUY", 1500, 180.25)
    # Order triggering safety boundary reject rules
    manager.process_order("ORD-002", "TSLA", "BUY", 5000, 220.00)

    print("\n=== STEP 3: EXECUTING RUNTIME HOT-SWAP TO V2 (NO RESTART) ===")
    manager.load_policy_dsl(v2_policy_dsl)
    
    print("\n=== STEP 4: PROCESSING ORIGINAL REJECTED ORDER VALUE UNDER NEW RULES ===")
    # Processing the larger transaction amount again to prove successful live updates
    manager.process_order("ORD-002-RETRY", "TSLA", "BUY", 5000, 220.00)
      
