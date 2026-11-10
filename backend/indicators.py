"""Technical indicators and candle patterns."""
import pandas as pd


def exponential_moving_average(series, period): return series.ewm(span=period, adjust=False).mean()
def wilder_average(series, period): return series.ewm(alpha=1 / period, adjust=False).mean()

def signal_from_vote(value): return "Compra" if value > 0 else "Venda" if value < 0 else "Neutro"

def find_price_action_patterns(price_data):
    """Identify recent reversal candles; prices are candle extremes, not forecasts."""
    candles = price_data.tail(41).reset_index(drop=True)
    signals = []
    for index in range(1, len(candles)):
        previous_candle, candle = candles.iloc[index - 1], candles.iloc[index]
        body = abs(candle.close - candle.open)
        spread = candle.high - candle.low
        if spread <= 0:
            continue
        lower = min(candle.open, candle.close) - candle.low
        upper = candle.high - max(candle.open, candle.close)
        prior = candles.iloc[max(0, index - 3):index]
        falling = candle.close > candle.open and previous_candle.close < previous_candle.open and previous_candle.close <= prior.close.iloc[0]
        rising = candle.close < candle.open and previous_candle.close > previous_candle.open and previous_candle.close >= prior.close.iloc[0]
        bullish_engulf = falling and candle.open <= previous_candle.close and candle.close >= previous_candle.open
        bearish_engulf = rising and candle.open >= previous_candle.close and candle.close <= previous_candle.open
        bullish_pin = falling and lower >= 2 * body and lower >= spread * 0.5 and upper <= spread * 0.25
        bearish_pin = rising and upper >= 2 * body and upper >= spread * 0.5 and lower <= spread * 0.25
        if bullish_engulf or bullish_pin:
            signals.append({"direction": "Alta", "price": float(candle.low), "time": int(candle.time),
                            "pattern": "Engolfo de alta" if bullish_engulf else "Rejeição de baixa (pavio inferior)"})
        elif bearish_engulf or bearish_pin:
            signals.append({"direction": "Baixa", "price": float(candle.high), "time": int(candle.time),
                            "pattern": "Engolfo de baixa" if bearish_engulf else "Rejeição de alta (pavio superior)"})
    return list(reversed(signals))[:3]

def analyze_indicators(price_data):
    close_prices, high_prices, low_prices = price_data["close"], price_data["high"], price_data["low"]
    last_close, indicator_results = close_prices.iloc[-1], []
    for period in (10, 20, 50, 100, 200):
        average_value = exponential_moving_average(close_prices, period).iloc[-1]
        indicator_results.append((f"EMA {period}", round(average_value, 2), signal_from_vote(1 if last_close > average_value else -1)))
    price_changes = close_prices.diff()
    rsi = 100 - 100 / (1 + wilder_average(price_changes.clip(lower=0), 14) / wilder_average(-price_changes.clip(upper=0), 14))
    rsi_value = rsi.iloc[-1]; indicator_results.append(("RSI 14", round(rsi_value, 1), signal_from_vote(1 if rsi_value < 30 else -1 if rsi_value > 70 else 0)))
    macd = exponential_moving_average(close_prices, 12) - exponential_moving_average(close_prices, 26); macd_histogram = macd - exponential_moving_average(macd, 9)
    indicator_results.append(("MACD", round(macd_histogram.iloc[-1], 2), signal_from_vote(1 if macd_histogram.iloc[-1] > 0 else -1)))
    lowest_low, highest_high = low_prices.rolling(14).min(), high_prices.rolling(14).max()
    stochastic = (100 * (close_prices - lowest_low) / (highest_high - lowest_low)).rolling(3).mean().iloc[-1]
    indicator_results.append(("Estocástico", round(stochastic, 1), signal_from_vote(1 if stochastic < 20 else -1 if stochastic > 80 else 0)))
    typical_price = (high_prices + low_prices + close_prices) / 3
    cci = ((typical_price - typical_price.rolling(20).mean()) / (0.015 * typical_price.rolling(20).apply(lambda item: abs(item - item.mean()).mean()))).iloc[-1]
    indicator_results.append(("CCI 20", round(cci, 1), signal_from_vote(1 if cci < -100 else -1 if cci > 100 else 0)))
    true_range = pd.concat([high_prices - low_prices, (high_prices - close_prices.shift()).abs(), (low_prices - close_prices.shift()).abs()], axis=1).max(axis=1)
    upward_move, downward_move = high_prices.diff(), -low_prices.diff()
    positive_movement = upward_move.where((upward_move > downward_move) & (upward_move > 0), 0.0); negative_movement = downward_move.where((downward_move > upward_move) & (downward_move > 0), 0.0)
    atr = wilder_average(true_range, 14); positive_directional_index, negative_directional_index = 100 * wilder_average(positive_movement, 14) / atr, 100 * wilder_average(negative_movement, 14) / atr
    adx = wilder_average(100 * (positive_directional_index - negative_directional_index).abs() / (positive_directional_index + negative_directional_index), 14).iloc[-1]
    indicator_results.append(("ADX 14", round(adx, 1), signal_from_vote((1 if positive_directional_index.iloc[-1] > negative_directional_index.iloc[-1] else -1) if adx > 25 else 0)))
    score = sum(1 if item[2] == "Compra" else -1 if item[2] == "Venda" else 0 for item in indicator_results) / len(indicator_results)
    label = ("Compra forte" if score >= 0.5 else "Compra" if score > 0.15 else
             "Venda forte" if score <= -0.5 else "Venda" if score < -0.15 else "Neutro")
    return {"label": label, "score": round(score, 2),
            "indicators": [{"name": name, "value": value, "signal": signal} for name, value, signal in indicator_results],
            "price_action": find_price_action_patterns(price_data)}

