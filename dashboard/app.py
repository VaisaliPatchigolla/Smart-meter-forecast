import streamlit as st
import pandas as pd
import requests
import datetime
import altair as alt

# Configuration
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Smart Meter Consumption Forecasting", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for cleaner UI (minimal)
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    h1 {
        font-weight: 600;
        margin-bottom: 0rem;
    }
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 1. HEADER
st.title("⚡ Smart Meter Consumption Forecasting")
st.markdown('<p class="subtitle">Forecast household electricity consumption for the next 7 days using historical smart-meter patterns.</p>', unsafe_allow_html=True)
st.markdown("---")

# Fetch households
@st.cache_data(ttl=300)
def get_households():
    try:
        response = requests.get(f"{API_URL}/households")
        response.raise_for_status()
        return response.json()
    except Exception:
        return []

households = get_households()

if households:
    # 2. HOUSEHOLD SELECTION
    st.subheader("Household")
    col_sel, col_sum1, col_sum2, col_sum3 = st.columns([1.5, 1, 1, 1])
    
    with col_sel:
        selected_hh = st.selectbox("Select Household", households, label_visibility="collapsed")
        
    if selected_hh:
        with st.spinner("Loading data..."):
            try:
                # API Call
                f_res = requests.get(f"{API_URL}/forecast/{selected_hh}")
                f_res.raise_for_status()
                forecast_data = f_res.json()["forecast"]
                
                # Prepare forecast df
                forecast_df = pd.DataFrame(forecast_data)
                forecast_df['date'] = pd.to_datetime(forecast_df['date'])
                forecast_df.rename(columns={'predicted_consumption_kwh': 'Consumption (kWh)'}, inplace=True)
                forecast_df['Type'] = 'Forecast'
                
                # Prepare history df
                history_df = pd.read_csv(r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting\data\processed\household_daily_100.csv")
                hh_hist = history_df[history_df['household_id'] == selected_hh].copy()
                hh_hist['date'] = pd.to_datetime(hh_hist['date'])
                
                last_30 = hh_hist.sort_values('date').tail(30).copy()
                last_30 = last_30[['date', 'consumption_kwh']]
                last_30.rename(columns={'consumption_kwh': 'Consumption (kWh)'}, inplace=True)
                last_30['Type'] = 'Actual'
                
                # Household Summary Calcs
                avg_daily = hh_hist['consumption_kwh'].mean()
                latest_actual = last_30.iloc[-1]['Consumption (kWh)']
                
                with col_sum1:
                    st.metric("Average Daily Consumption", f"{avg_daily:.2f} kWh")
                with col_sum2:
                    st.metric("Latest Actual", f"{latest_actual:.2f} kWh")
                with col_sum3:
                    st.metric("Forecast Horizon", "7 Days")
                
                st.markdown("---")
                
                # 3. MODEL PERFORMANCE
                st.subheader("OVERALL MVP BACKTEST METRICS")
                st.caption("Measured using a strict recursive 7-day backtest.")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("7-Day MAE", "2.532 kWh")
                m2.metric("7-Day RMSE", "4.393 kWh")
                m3.metric("Baseline MAE", "3.090 kWh")
                m4.metric("MAE Improvement", "18.05%")
                
                st.markdown("---")
                
                # 4. MAIN FORECAST CHART
                st.subheader("7-DAY CONSUMPTION FORECAST")
                
                combined_df = pd.concat([last_30, forecast_df])
                
                # Altair Chart for better control
                base = alt.Chart(combined_df).encode(
                    x=alt.X('date:T', axis=alt.Axis(title='Date', format='%d %b', labelAngle=-45, tickCount=10)),
                    y=alt.Y('Consumption (kWh):Q', axis=alt.Axis(title='Consumption (kWh)')),
                    color=alt.Color('Type:N', scale=alt.Scale(domain=['Actual', 'Forecast'], range=['#2c3e50', '#e74c3c']), legend=alt.Legend(title=None, orient='top-right')),
                    tooltip=[alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'), alt.Tooltip('Consumption (kWh):Q', title='kWh', format='.2f'), 'Type:N']
                )
                
                line = base.mark_line(point=True, strokeWidth=2)
                
                # Add vertical rule at the split
                split_date = last_30['date'].max()
                rule = alt.Chart(pd.DataFrame({'date': [split_date]})).mark_rule(color='gray', strokeDash=[4,4]).encode(x='date:T')
                
                chart = (line + rule).properties(height=400).interactive()
                st.altair_chart(chart, use_container_width=True)
                
                st.markdown("---")
                
                # 5. FORECAST DETAILS & MODEL INFO
                col_tbl, col_info = st.columns([1, 1.5])
                
                with col_tbl:
                    st.subheader("7-Day Forecast Details")
                    display_df = forecast_df[['date', 'Consumption (kWh)']].copy()
                    display_df['date'] = display_df['date'].dt.strftime('%d %b %Y')
                    display_df['Consumption (kWh)'] = display_df['Consumption (kWh)'].apply(lambda x: f"{x:.2f} kWh")
                    display_df.rename(columns={'date': 'Date', 'Consumption (kWh)': 'Predicted Consumption'}, inplace=True)
                    st.dataframe(display_df, hide_index=True, use_container_width=True)
                    
                with col_info:
                    # 6. MODEL INFORMATION
                    st.subheader("Model Information")
                    st.markdown("""
                    **Model:** LightGBM Regression  
                    **Target:** Daily electricity consumption (kWh)  
                    **Forecast Horizon:** 7 days  
                    **Training Households:** 100  
                    **Historical Period:** 2012-01-01 → 2013-12-31  
                    **Forecasting Method:** Recursive multi-step forecasting
                    """)
                    
                    # 7. HOW THE FORECAST WORKS
                    with st.expander("How this forecast works"):
                        st.write("The model analyzes historical household consumption, recent consumption patterns, weekly patterns, seasonal behavior and calendar information to estimate electricity consumption for the next 7 days.")
                        st.caption("Current MVP limitation: weather data is not included.")
                        
            except Exception as e:
                st.error("Forecast generation failed. Please try again later.")
else:
    st.error("Failed to load households. Is the API running?")
