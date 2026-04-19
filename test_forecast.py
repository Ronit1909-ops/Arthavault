from prophet import Prophet
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import logging
logging.getLogger('prophet').setLevel(logging.ERROR)

# Simulate 237 transactions over 3 months
np.random.seed(42)
dates = [datetime(2026, 1, 1) + timedelta(days=i//3) for i in range(237)]
amounts = np.random.uniform(50, 5000, 237)

df = pd.DataFrame({'date': dates, 'amount': amounts})
df['ds'] = pd.to_datetime(df['date']).dt.normalize()
daily = df.groupby('ds')['amount'].sum().reset_index().rename(columns={'amount': 'y'})
print(f'Daily rows: {len(daily)}')

m = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False, interval_width=0.80)
m.fit(daily)
future = m.make_future_dataframe(periods=30)
forecast = m.predict(future)
last = daily['ds'].max()
fut = forecast[forecast['ds'] > last].tail(30)
print(f'Forecast rows: {len(fut)}')
print(f'Sample date: {fut.iloc[0]["ds"].date()}  yhat: {fut.iloc[0]["yhat"]:.2f}')
print('FORECAST OK')
