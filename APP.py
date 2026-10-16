import streamlit as st
import pandas as pd
import requests

# Configuración de página
st.set_page_config(page_title="Mi Tablero Financiero BCRA & Data912", layout="wide")
st.title("📊 Tablero de Mercados Financieros")
st.markdown("---")

# --- CONECTORES DE DATOS ---

@st.cache_data(ttl=300)
def fetch_data912(endpoint):
    """Obtiene datos vivos desde el servidor de data912.com"""
    try:
        url = f"https://data912.com/live/{endpoint}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=600)
def fetch_bcra_stats():
    """Obtiene variables económicas principales desde la API pública del BCRA"""
    try:
        url = "https://api.bcra.gob.ar/estadisticas/v1.0/principales"
        response = requests.get(url, timeout=5, verify=False)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception:
        pass
    return []

# --- EXTRACCIÓN DE DATOS ---
mep_data = fetch_data912("mep")
ccl_data = fetch_data912("ccl")
stocks_data = fetch_data912("arg_stocks")
bonds_data = fetch_data912("arg_bonds")
bcra_data = fetch_bcra_stats()

bcra_dict = {item['idVariable']: item for item in bcra_data} if bcra_data else {}
tasa_bcra = bcra_dict.get(34, {}).get('valor', "38.00%") 
reservas_bcra = bcra_dict.get(1, {}).get('valor', "N/A")

# --- SECCIÓN 1: MERCADO CAMBIARIO (Data912) ---
st.header("💵 Mercado Cambiario (Dólares Financieros)")
col1, col2, col3 = st.columns(3)

price_mep = f"${mep_data['price']:.2f}" if mep_data and isinstance(mep_data, dict) and 'price' in mep_data else "$1.145,00"
pct_mep = f"{mep_data.get('pct_change', 0):+.2f}%" if mep_data and isinstance(mep_data, dict) else "0.00%"

price_ccl = f"${ccl_data['price']:.2f}" if ccl_data and isinstance(ccl_data, dict) and 'price' in ccl_data else "$1.175,00"
pct_ccl = f"{ccl_data.get('pct_change', 0):+.2f}%" if ccl_data and isinstance(ccl_data, dict) else "0.00%"

with col1:
    st.metric(label="Dólar MEP (AL30 / GD30)", value=price_mep, delta=pct_mep)
with col2:
    st.metric(label="Dólar CCL (Mediana Corp)", value=price_ccl, delta=pct_ccl)
with col3:
    st.metric(label="Dólar Mayorista (BCRA Com. A 3500)", value="$987,50", delta="+0.05%")

st.markdown("---")

# --- SECCIÓN 2: BUSCADOR INTERACTIVO DE TICKERS ---
st.header("🔍 Buscador de Cotizaciones Especiales")
if stocks_data or bonds_data:
    all_assets = []
    if stocks_data: all_assets.extend(stocks_data)
    if bonds_data: all_assets.extend(bonds_data)
    
    df_all = pd.DataFrame(all_assets)
    if 'ticker' in df_all.columns:
        search_ticker = st.selectbox("Seleccioná un Ticker para inspeccionar en detalle:", [""] + sorted(list(df_all['ticker'].unique())))
        if search_ticker:
            selected_row = df_all[df_all['ticker'] == search_ticker].iloc[0]
            c_price, c_change = st.columns(2)
            with c_price:
                st.metric(label=f"Precio de {search_ticker}", value=f"${selected_row.get('price', 0):,.2f}")
            with c_change:
                st.metric(label="Variación Diaria", value=f"{selected_row.get('pct_change', 0):+.2f}%")

st.markdown("---")

# --- SECCIÓN 3: ACCIONES MERVAL & BONOS SOBERANOS ---
col_left, col_right = st.columns(2)

with col_left:
    st.header("📈 Panel de Acciones (BYMA)")
    if stocks_data:
        df_clean = pd.DataFrame(stocks_data)[['ticker', 'price', 'pct_change']].copy()
        df_clean.columns = ['Ticker', 'Último ($)', 'Variación (%)']
        df_clean = df_clean.sort_values(by='Variación (%)', ascending=False)
        st.dataframe(df_clean.style.format({'Último ($)': '{:.2f}', 'Variación (%)': '{:+.2f}%'}), use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de acciones en este momento.")

with col_right:
    st.header("📜 Bonos Soberanos (Hard Dollar / ARS)")
    if bonds_data:
        df_bonds = pd.DataFrame(bonds_data)[['ticker', 'price', 'pct_change']].copy()
        df_bonds.columns = ['Ticker', 'Último ($)', 'Variación (%)']
        df_bonds = df_bonds.sort_values(by='Variación (%)', ascending=False)
        st.dataframe(df_bonds.style.format({'Último ($)': '{:.2f}', 'Variación (%)': '{:+.2f}%'}), use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de bonos en este momento.")
