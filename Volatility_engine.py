import numpy as np
import pandas as pd
from arch import arch_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler

class HybridVolatilityEngine:
    """
    An institutional-grade volatility forecasting engine that combines 
    a statistical GARCH(1,1) model with an LSTM neural network to predict
    dynamic market regimes and daily implied volatility.
    """
    def __init__(self, lstm_lookback=20):
        self.lstm_lookback = lstm_lookback
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.lstm_model = None
        
    def fit_garch_residuals(self, returns):
        """
        Fits a baseline GARCH(1,1) model to extract conditional volatility
        and standardized residuals for neural network conditioning.
        """
        # Scale returns by 100 for numerical stability during MLE estimation
        scaled_returns = returns * 100
        garch = arch_model(scaled_returns, vol='Garch', p=1, q=1, dist='normal')
        garch_res = garch.fit(disp='off')
        
        # Scale conditional volatility back to the original return scale
        garch_vol = garch_res.conditional_volatility / 100
        standardized_res = garch_res.resid / garch_res.conditional_volatility
        
        return garch_vol, standardized_res

    def _prepare_lstm_data(self, data):
        """Creates sliding lookback windows to train the LSTM sequence network."""
        X, y = [], []
        for i in range(len(data) - self.lstm_lookback):
            X.append(data[i:(i + self.lstm_lookback)])
            y.append(data[i + self.lstm_lookback])
        return np.array(X), np.array(y)

    def build_and_train_lstm(self, standardized_residuals, epochs=15, batch_size=32):
        """
        Trains an LSTM network to isolate non-linear clustering patterns
        and hidden regimes inside the GARCH standardized residuals.
        """
        reshaped_res = standardized_residuals.values.reshape(-1, 1)
        scaled_res = self.scaler.fit_transform(reshaped_res)
        
        X, y = self._prepare_lstm_data(scaled_res)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        # Deep time-series sequence layout
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.lstm_lookback, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=0)
        self.lstm_model = model

    def forecast_next_day_volatility(self, returns, garch_vol, standardized_residuals):
        """
        Synthesizes the linear GARCH projection with the non-linear LSTM
        residual adjustment to yield the final dynamic market volatility factor.
        """
        # Shape the most recent window of residuals for inference
        recent_res = standardized_residuals.values[-self.lstm_lookback:].reshape(-1, 1)
        scaled_recent = self.scaler.transform(recent_res)
        X_input = np.reshape(scaled_recent, (1, self.lstm_lookback, 1))
        
        # Predict the step-ahead residual adjustment
        predicted_scaled_res = self.lstm_model.predict(X_input, verbose=0)
        predicted_res = self.scaler.inverse_transform(predicted_scaled_res)[0][0]
        
        # Re-estimate the baseline one-step-ahead GARCH variance projection
        scaled_returns = returns * 100
        garch = arch_model(scaled_returns, vol='Garch', p=1, q=1)
        garch_res = garch.fit(disp='off')
        forecasts = garch_res.forecast(horizon=1)
        
        next_day_garch_vol = np.sqrt(forecasts.variance.values[-1, 0]) / 100
        
        # Hybrid Synthesis optimization rule
        hybrid_vol_forecast = next_day_garch_vol * (1 + abs(predicted_res))
        return hybrid_vol_forecast
  
