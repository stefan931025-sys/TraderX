import numpy as np
import pandas as pd

class MarketDataStream:
    """
    Generates synthetic financial time-series data reflecting structural 
    macroeconomic regime shifts, volatility clustering, and volume spikes.
    """
    def __init__(self, random_seed=42):
        self.random_seed = random_seed
        
    def generate_regime_switching_data(self, n_days=500):
        """
        Simulates asset returns and volumes evolving across two distinct 
        market regimes using a Markov chain transition matrix.
        """
        np.random.seed(self.random_seed)
        
        returns = np.zeros(n_days)
        volumes = np.zeros(n_days)
        regimes = np.zeros(n_days)
        
        # Initial states
        current_regime = 0  # 0 for Low Volatility, 1 for High Volatility Crisis
        current_vol = 0.01
        
        for t in range(n_days):
            # Markov transition probabilities
            if current_regime == 0:
                # 3% probability to shift from low-vol to high-vol crisis
                if np.random.rand() < 0.03:
                    current_regime = 1
            else:
                # 8% probability to mean-revert back to calm accumulation
                if np.random.rand() < 0.08:
                    current_regime = 0
            
            regimes[t] = current_regime
            
            # Volatility clustering dynamics (GARCH-style evolution)
            if current_regime == 0:
                # Low-volatility regime: tight variances, steady positive drift
                if t > 0:
                    current_vol = np.sqrt(0.00002 + 0.1 * (returns[t-1]**2) + 0.85 * (current_vol**2))
                else:
                    current_vol = 0.01
                innov = np.random.normal(0.0002, current_vol)
                volume = np.random.normal(1_000_000, 150_000)
            else:
                # High-volatility crisis regime: wider variances, negative return skew, massive volume
                if t > 0:
                    current_vol = np.sqrt(0.0002 + 0.15 * (returns[t-1]**2) + 0.80 * (current_vol**2))
                else:
                    current_vol = 0.04
                innov = np.random.normal(-0.001, current_vol)
                volume = np.random.normal(2_500_000, 500_000)
                
            returns[t] = innov
            volumes[t] = max(100_000, volume)  # Enforce liquidity floor
            
        # Build business day index ending today
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq='B')
        
        df = pd.DataFrame({
            'Return': returns,
            'Volume': volumes,
            'Regime_Label': regimes
        }, index=dates)
        
        return df

if __name__ == "__main__":
    # Smoke test validation
    stream = MarketDataStream()
    test_data = stream.generate_regime_switching_data(n_days=100)
    print(f"Data Stream initialized. Generated shape: {test_data.shape}")
