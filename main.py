import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
from urllib.parse import urlencode

#Global
selected_month = None
selected_device = None
months_available = None
devices_available = None

st.set_page_config(layout='wide')


# URL's de requisição
startDate = "2022-06-01 03:00:00+00"
endDate = "2024-07-01 04:00:00+00"
params = urlencode({"startDate": startDate, "endDate": endDate})

url_api = "http://localhost:3000/api/reports/"
url_report_consumption_analysis = "consumption-analysis"
url_report_active_power = f"active-power?{params}"
url_consumption_patterns = f"consumption-patterns?{params}"
url_devices_and_months = "devices-and-months"


def set_up_dashboard():
    st.title("Greenant - Matheus Costa")
    st.subheader(f"Dispositivo: {selected_device} | Mês: {selected_month}")

    col1, = st.columns(1)
    col2, col3 = st.columns(2)
    return col1, col2, col3

def set_devices_and_months():
    global months_available, devices_available
    response = requests.get(url_api + url_devices_and_months)
    if response.status_code == 200:
        data = response.json()
        months_available = data["months"]
        devices_available = data["devices"]

def update_global_filters():
    global selected_month, selected_device
    st.sidebar.title("Filtros")
    selected_month = st.sidebar.selectbox("Escolha o mês para análise", options=months_available)

    devices_available.insert(0, "Todos")
    selected_device = st.sidebar.selectbox("Escolha o dispositivo", options=devices_available)


def request(url):
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(e)
        return None
    
def criar_grafico_padroes_consumo(data_padroes_consumo):
    peak_hours = data_padroes_consumo["peakHours"]
    lowest_hours = data_padroes_consumo["lowestHours"]
    
    df_peak = pd.DataFrame(peak_hours)
    df_lowest = pd.DataFrame(lowest_hours)
    df_peak["type"] = "Peak Hours"
    df_lowest["type"] = "Lowest Hours"

    df_combined = pd.concat([df_peak, df_lowest])

    df_combined['hour'] = pd.to_datetime(df_combined['hour'])
    df_combined['month'] = df_combined['hour'].dt.to_period('M')

    df_combined['device_type'] = df_combined['deviceId'] + ' - ' + df_combined['type']
    color_discrete_map = {
        device_type: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, device_type in enumerate(df_combined['device_type'].unique())
    }

    if selected_device == "Todos":
        df_filtered = df_combined[df_combined['month'] == selected_month]
    else:
        df_filtered = df_combined[(df_combined['month'] == selected_month) & (df_combined['deviceId'] == selected_device)]

    df_filtered.sort_values('hour', inplace=True)

    average_consumption = data_padroes_consumo["averageConsumption"]
    graph = px.bar(df_filtered, x='hour', y='energyPerHour', color='device_type', color_discrete_map=color_discrete_map,
                title='Padrões de Consumo: Horários de Pico e Menor Uso (Wh)',
                barmode='group')

    # Adicionando a linha de média
    graph.add_trace(go.Scatter(
        x=df_filtered['hour'],
        y=[average_consumption] * len(df_filtered),
        mode='lines',
        name='Média',
        line=dict(color='firebrick', width=2, dash='dash')
    ))
    graph.update_layout(xaxis_title='Hora (h)', yaxis_title='Energia Consumida (Wh)',showlegend=True,  legend_title_text='Dispositivos')

    return graph

def criar_grafico_potencia_ativa(data_potencia_ativa):
    df = pd.DataFrame(data_potencia_ativa)
    df['hour'] = pd.to_datetime(df['hour'])
    df['month'] = df['hour'].dt.to_period('M')

    if selected_device == "Todos":
        df_filtered = df[df['month'] == selected_month]
    else:
        df_filtered = df[(df['month'] == selected_month) & (df['deviceId'] == selected_device)]

    graph = px.line(df_filtered, x='hour', y='activePowerPerHour', color='deviceId', 
                title='Comparação da Potência Ativa Média entre dispositivos (W/h)')
    
    graph.update_layout(xaxis_title='Hora (h)', yaxis_title='Potência ativa média(W)',showlegend=True,  legend_title_text='Dispositivos')
    return graph

def criar_grafico_consumo_energia(data_consumo_energia):
    average_power = data_consumo_energia["avgPowerPerDay"]
    active_energy = data_consumo_energia["activeEnergyPerDay"]

    df_power = pd.DataFrame(average_power)
    df_energy = pd.DataFrame(active_energy)

    df_power["type"] = "avg_power_per_day"
    df_energy["type"] = "active_energy"

    df_combined = pd.concat([df_power, df_energy])
    df_combined['date'] = pd.to_datetime(df_combined['date'])
    df_combined['month'] = df_combined['date'].dt.to_period('M')
    df_combined['device_type'] = df_combined['deviceId'] + ' - ' + df_combined['type']

    color_discrete_map = {
        device_type: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, device_type in enumerate(df_combined['device_type'].unique())
    }

    if selected_device == "Todos":
        df_filtered = df_combined[df_combined['month'] == selected_month]
    else:
        df_filtered = df_combined[(df_combined['month'] == selected_month) & (df_combined['deviceId'] == selected_device)]

    graph = px.bar(df_filtered, x='date', y=['activeEnergyPerDay', 'avgPowerPerDay'], color='device_type', color_discrete_map=color_discrete_map,
                title='Consumo de energia e potência ativa ao longo do tempo',
                barmode='group')

    graph.update_layout(xaxis_title='Dia', yaxis_title='Energia Consumida (W)',showlegend=True,  legend_title_text='Dispositivos')

    return graph


def main():
    try:
        set_devices_and_months()
        update_global_filters()

        col1, col2, col3 = set_up_dashboard()

        data_consumo_energia = request(url_api + url_report_consumption_analysis)
        data_potencia_ativa = request(url_api + url_report_active_power)
        data_padroes_consumo = request(url_api + url_consumption_patterns)
        
        if not data_consumo_energia or not data_potencia_ativa or not data_padroes_consumo:
            st.error("Erro ao carregar os dados")
            return
        
        graph_2 = criar_grafico_consumo_energia(data_consumo_energia)
        col1.plotly_chart(graph_2)

        graph_3 = criar_grafico_potencia_ativa(data_potencia_ativa)
        col2.plotly_chart(graph_3)

        graph_1 = criar_grafico_padroes_consumo(data_padroes_consumo)
        col3.plotly_chart(graph_1)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()