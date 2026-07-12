import numpy as np
import pandas as pd
from market_data_stream import MarketDataStream
from volatility_engine import HybridVolatilityEngine

class AlgorithmicOrderManager:
    """
    An institutional execution system that optimizes order slicing and volume 
    participation based on dynamic GARCH-LSTM volatility forecasts.
    """
    def __init__(self, target_participation_rate=0.10):
        self.target_rate = target_participation_rate
        self.data_stream = MarketDataStream()
        self.vol_engine = HybridVolatilityEngine()

    def calculate_dynamic_order_size(self, market_volume, current_returns):
        """
        Processes historical returns to compute step-ahead volatility projections, 
        dynamically scaling down maximum exposure during high-risk regimes.
        """
        # 1. Extract conditions and fit models using the hybrid pipeline
        garch_vol, standardized_res = self.vol_engine.fit_garch_residuals(current_returns)
        
        # Train internal LSTM architecture on extracted residuals
        self.vol_engine.build_and_train_lstm(standardized_res, epochs=5, batch_size=16)
        
        # 2. Extract synthesized predictive volatility
        predicted_vol = self.vol_engine.forecast_next_day_volatility(
            current_returns, garch_vol, standardized_res
        )
        
        # 3. Dynamic Risk Overlay adjustment rule
        # If predicted daily volatility spikes above 2.5%, downscale the participation rate
        risk_scalar = 1.0
        if predicted_vol > 0.025:
            risk_scalar = 0.5  # Cut risk in half during high-volatility conditions
            
        adjusted_rate = self.target_rate * risk_scalar
        target_order_size = int(market_volume * adjusted_rate)
        
        return max(100, target_order_size), predicted_vol

    def execute_trading_session_simulation(self, historical_days=250):
        """
        Simulates an execution session over structural market regimes, 
        outputting real-time risk adjustments and execution slices.
        """
        # Generate structural regime data from the stream
        market_df = self.data_stream.generate_regime_switching_data(n_days=historical_days)
        
        print("==================================================================")
        print("          INITIALIZING HYBRID VOLATILITY ORDER MANAGEMENT         ")
        print("==================================================================")
        
        # Run execution loop on the most recent slice of data
        lookback = 100
        session_returns = market_df['Return'].iloc[-lookback:]
        session_volumes = market_df['Volume'].iloc[-lookback:]
        
        # Target slice execution test
        current_vol_series = session_returns.iloc[:-1]
        latest_volume = session_volumes.iloc[-1]
        
        order_size, forecasted_vol = self.calculate_dynamic_order_size(latest_volume, current_vol_series)
        
        print(f"Current Target Volume: {latest_volume:,.0f} shares")
        print(f"Forecasted Hybrid Volatility: {forecasted_vol * 100:.2f}%")
        print(f"Risk-Adjusted Order Allocation Size: {order_size:,} shares")
        print("==================================================================")
        
        return order_size

if __name__ == "__main__":
    manager = AlgorithmicOrderManager()
    manager.execute_trading_session_simulation()
