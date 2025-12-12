import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time

# Importiamo la logica dal core
from price_tracker_core import ProductRanking, get_mock_data, PriceIntelligenceEngine

# ==============================================================================
# CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Price Intelligence Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stDataFrame { border: 1px solid #f0f2f6; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNZIONI DI SUPPORTO
# ==============================================================================

def extract_brand(product_name):
    """Estrae il brand dal nome del prodotto (Euristica semplice per demo)"""
    # Lista di brand noti multi-parola per evitare errori
    known_brands = ["Acqua di Parma", "Jean Paul Gaultier", "Yves Saint Laurent", "Dolce & Gabbana"]
    for brand in known_brands:
        if product_name.lower().startswith(brand.lower()):
            return brand
    # Fallback: prende la prima parola
    return product_name.split()[0]

@st.cache_data
def load_data():
    """Carica i dati e li processa."""
    raw_data = get_mock_data()
    products = [ProductRanking(**item) for item in raw_data]
    analyzed_products = PriceIntelligenceEngine.enrich_data(products)
    
    data_list = []
    for p in analyzed_products:
        # Logica simulata status
        alert_level = "🟢 Stable"
        if not p.is_winning and p.popularity_index <= 5:
            alert_level = "🔴 CRITICAL" if (p.total_cost - p.min_price_shipping_market) > 1 else "🟡 Warning"

        winner = "Noi (👑)" if p.is_winning else (p.best_offers[0].merchant if p.best_offers else "N/A")
        brand = extract_brand(p.product_name)

        data_list.append({
            "SKU": p.sku,
            "Prodotto": p.product_name,
            "Brand": brand,        # Nuovo campo
            "Categoria": p.category, 
            "Mio Prezzo": p.total_cost,
            "Min Mercato": p.min_price_shipping_market,
            "Gap (€)": p.price_gap,
            "Rank": p.rank_with_shipping,
            "Competitor Top": winner,
            "Popolarità": p.popularity_index,
            "Status": alert_level,
            "object": p 
        })
    
    return pd.DataFrame(data_list)

def generate_sparkline_data(base_price, trend='stable'):
    """Genera dati finti per il grafico"""
    dates = [datetime.now() - timedelta(days=i) for i in range(14, 0, -1)]
    prices = []
    current = base_price
    for _ in range(14):
        change = random.uniform(-0.5, 0.5)
        if trend == 'down': change -= 0.1
        current += change
        prices.append(max(current, base_price * 0.8))
    return pd.DataFrame({"Data": dates, "Prezzo Mercato": prices})

# ==============================================================================
# LOGICA PRINCIPALE & SIDEBAR
# ==============================================================================

# Caricamento Dati Iniziale (per popolare i filtri)
df = load_data()

with st.sidebar:
    st.title("⚙️ Configurazioni")
    
    api_key = st.text_input("Trovaprezzi API Key", type="password")
    st.divider()
    
    st.subheader("Filtri Avanzati")
    
    # 1. FILTRO CATEGORIA
    available_categories = sorted(df["Categoria"].unique())
    selected_categories = st.multiselect(
        "📂 Categoria",
        options=available_categories,
        default=available_categories,
        placeholder="Tutte le categorie"
    )

    # 2. FILTRO BRAND (NUOVO)
    available_brands = sorted(df["Brand"].unique())
    selected_brands = st.multiselect(
        "🏷️ Brand",
        options=available_brands,
        default=available_brands,
        placeholder="Tutti i brand"
    )

    # 3. FILTRO COMPETITOR (NUOVO - Chi vince la Buy Box)
    available_competitors = sorted(df["Competitor Top"].unique())
    selected_competitors = st.multiselect(
        "🏆 Competitor Vincente",
        options=available_competitors,
        default=available_competitors,
        placeholder="Tutti i competitor"
    )

    # 4. FILTRO STATUS
    status_filter = st.multiselect(
        "🚦 Status Alert",
        ["🟢 Stable", "🟡 Warning", "🔴 CRITICAL"],
        default=["🟢 Stable", "🟡 Warning", "🔴 CRITICAL"]
    )
    
    st.info("💡 I dati vengono aggiornati automaticamente ogni mattina alle 05:00.")
    
    if st.button("🔄 Aggiorna Dati Ora"):
        with st.spinner('Scraping in corso...'):
            time.sleep(1.5)
            st.cache_data.clear()
            st.success("Dati aggiornati!")
            st.rerun()

# ==============================================================================
# DASHBOARD BODY
# ==============================================================================

st.title("📊 Competitor Price Intelligence")
st.markdown("Monitoraggio real-time dei prezzi e ottimizzazione margini.")

# APPLICAZIONE FILTRI COMBINATI
df_filtered = df[
    (df["Status"].isin(status_filter)) & 
    (df["Categoria"].isin(selected_categories)) &
    (df["Brand"].isin(selected_brands)) &
    (df["Competitor Top"].isin(selected_competitors))
]

if df_filtered.empty:
    st.warning("Nessun prodotto corrisponde ai filtri selezionati.")
else:
    # 1. KPI SECTION
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        winning_products = len(df_filtered[df_filtered['Rank'] == 1])
        st.metric(label="Prodotti Rank #1", value=f"{winning_products}", delta="Sulla selezione")

    with col2:
        critical_items = len(df_filtered[df_filtered['Status'] == "🔴 CRITICAL"])
        st.metric(label="Alert Critici", value=critical_items, delta_color="inverse")

    with col3:
        avg_gap = df_filtered[df_filtered['Rank'] > 1]['Gap (€)'].mean()
        if pd.isna(avg_gap): avg_gap = 0.0
        st.metric(label="Gap Medio", value=f"€ {avg_gap:.2f}", delta_color="off")

    with col4:
        st.metric(label="Prodotti Visibili", value=len(df_filtered))

    st.markdown("---")

    # 2. TABELLA PRINCIPALE
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Panoramica Prodotti")
        
        event = st.dataframe(
            df_filtered.drop(columns=["object"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Categoria": st.column_config.TextColumn("Cat.", width="small"),
                "Brand": st.column_config.TextColumn("Brand", width="small"), # Mostriamo anche il Brand in tabella
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                "Gap (€)": st.column_config.NumberColumn("Gap", format="€ %.2f"),
                "Mio Prezzo": st.column_config.NumberColumn("Mio Prezzo", format="€ %.2f"),
                "Min Mercato": st.column_config.NumberColumn("Min Mercato", format="€ %.2f"),
                "Competitor Top": st.column_config.TextColumn("Winner", width="medium"),
            },
            selection_mode="single-row",
            on_select="rerun"
        )

    # 3. DETTAGLIO PRODOTTO
    with col_right:
        selection = event.selection.rows
        if selection:
            selected_index = selection[0]
            selected_row = df_filtered.iloc[selected_index]
            product_obj = selected_row["object"]
            
            st.subheader(f"🔍 {product_obj.sku}")
            st.caption(f"{selected_row['Brand']} - {selected_row['Prodotto']}")
            
            st.markdown(f"""
            <div style="background-color: #e0e7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-bottom: 20px;">
                <strong>🤖 AI Strategy:</strong><br>
                {'Il competitor ' + selected_row['Competitor Top'] + ' è aggressivo.' if selected_row['Status'] == '🔴 CRITICAL' else 'Posizionamento ottimale.'}
                <br><em>Consiglio: {f"Target Price € {selected_row['Min Mercato'] - 0.10:.2f}" if selected_row['Status'] == '🔴 CRITICAL' else "Mantieni prezzo."}</em>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Trend Prezzo (14gg)**")
            chart_data = generate_sparkline_data(selected_row["Min Mercato"], trend='down' if selected_row['Status'] == '🔴 CRITICAL' else 'stable')
            
            fig = px.line(chart_data, x="Data", y="Prezzo Mercato", markers=True)
            fig.add_hline(y=selected_row["Mio Prezzo"], line_dash="dash", line_color="red", annotation_text="Tu")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("👈 Seleziona un prodotto per l'analisi dettagliata.")

st.caption("Developed with ❤️ using Streamlit & Python")
