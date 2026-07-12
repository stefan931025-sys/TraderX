# TraderX: Institutional Portfolio Rebalancer & Hybrid Volatility Execution Engine

TraderX is an advanced quantitative execution framework that combines classical financial econometrics with deep sequence neural networks to dynamically optimize order slicing and execution algorithms. By decoupling structural volatility estimation from machine learning sequence layers, the system prevents execution degradation during rapid market regime shifts.

## 🏗️ System Architecture & Modularity

The framework is strictly decoupled to ensure high computational performance and clean separation of concerns:
1. **`volatility_engine.py`**: Houses the mathematical core (`HybridVolatilityEngine`). It leverages maximum likelihood estimation for structural parameter estimation and trains sequence networks on standardized data structures.
2. **`market_data_stream.py`**: A validation data pipeline (`MarketDataStream`) that simulates multi-regime asset dynamics using a discrete-time Markov chain transition matrix to test execution models under liquidity drops and market stress.
3. **`algorithmic_order_manager.py`**: The central execution orchestrator (`AlgorithmicOrderManager`). It ingests the hybrid volatility forecasts to dynamically scale the risk overlay and compute volume participation constraints in real-time.

---

## 🧮 Mathematical Core

The system utilizes a two-stage predictive synthesis to model asset risk:

### 1. Structural Time-Series Layer
A classical conditional variance $GARCH(1,1)$ model isolates linear time-varying variance clustering from asset returns:

$$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

Where the residuals are scaled for numerical stability during MLE optimization:

$$\epsilon_t = \sigma_t z_t \quad \text{where} \quad z_t \sim \mathcal{N}(0, 1)$$

### 2. Deep Learning Sequence Layer
Standardized residuals ($z_t$) are extracted and routed into a deep Long Short-Term Memory (LSTM) recurrent network to isolate hidden non-linear regime transitions and asymmetric clustering patterns:

$$f_{\text{LSTM}}(z_{t-k}, \dots, z_{t-1}) \to \hat{z}_t$$

### 3. Hybrid Synthesis & Execution Adjustment
The execution engine unifies the linear baseline volatility prediction with the non-linear deep learning error factor using an institutional synthesis rule:

$$\sigma_{\text{hybrid}} = \sigma_{\text{GARCH}, t} \cdot (1 + |\hat{z}_t|)$$

If the synthesized daily forecast spikes beyond target risk boundaries ($\sigma_{\text{hybrid}} > 2.5\%$), a dynamic risk overlay scales back the target volume participation rate by $50\%$ to mitigate market impact and protect portfolio capital.

---

## 🚀 Getting Started

### Prerequisites
Ensure your environment meets the dependency constraints specified in `requirements.txt`:
```text
numpy>=1.20.0
pandas>=1.3.0
arch>=5.0
tensorflow>=2.6.0
scikit-learn>=1.0
