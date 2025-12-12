import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time

# Importiamo la logica dal nostro core (assicurati che price_tracker_core.py sia nella stessa cartella)
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

# Stile CSS custom per rendere la dashboard più "figa"
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

@st.cache_data
def load_data():
    """
    Carica i dati simulati e li processa. 
    Usa la cache di Streamlit per non ricalcolare a ogni click.
    """
    # 1. Recupera dati grezzi dal Core
    raw_data = get_mock_data()
    products = [ProductRanking(**item) for item in raw_data]
    
    # 2. Arricchisce i dati con la logica Business (Gap, Alert)
    analyzed_products = PriceIntelligenceEngine.enrich_data(products)
    
    # 3. Converte in DataFrame Pandas per facilitare la visualizzazione
    data_list = []
    for p in analyzed_products:
        # Logica simulata per status alert (la stessa del service precedente)
        alert_level = "🟢 Stable"
        if not p.is_winning and p.popularity_index <= 5:
            alert_level = "🔴 CRITICAL" if (p.total_cost - p.min_price_shipping_market) > 1 else "🟡 Warning"

        # Troviamo il competitor vincente
        winner = "Noi (👑)" if p.is_winning else (p.best_offers[0].merchant if p.best_offers else "N/A")

        data_list.append({
            "SKU": p.sku,
            "Prodotto": p.product_name,
            "Mio Prezzo": p.total_cost,
            "Min Mercato": p.min_price_shipping_market,
            "Gap (€)": p.price_gap,
            "Rank": p.rank_with_shipping,
            "Competitor Top": winner,
            "Popolarità": p.popularity_index,
            "Status": alert_level,
            "object": p # Salviamo l'oggetto completo per i dettagli
        })
    
    return pd.DataFrame(data_list)

def generate_sparkline_data(base_price, trend='stable'):
    """Genera dati finti per il grafico storico"""
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
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("⚙️ Configurazioni")
    
    # Simulazione input API Key
    api_key = st.text_input("Trovaprezzi API Key", type="password")
    
    st.divider()
    
    st.subheader("Filtri")
    status_filter = st.multiselect(
        "Filtra per Status",
        ["🟢 Stable", "🟡 Warning", "🔴 CRITICAL"],
        default=["🟢 Stable", "🟡 Warning", "🔴 CRITICAL"]
    )
    
    st.info("💡 I dati vengono aggiornati automaticamente ogni mattina alle 05:00.")
    
    if st.button("🔄 Aggiorna Dati Ora"):
        with st.spinner('Scraping in corso...'):
            time.sleep(1.5) # Fake loading
            st.cache_data.clear()
            st.success("Dati aggiornati!")
            st.rerun()

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

st.title("📊 Competitor Price Intelligence")
st.markdown("Monitoraggio real-time dei prezzi e ottimizzazione margini.")

# Caricamento Dati
df = load_data()
df_filtered = df[df["Status"].isin(status_filter)]

# 1. KPI SECTION
col1, col2, col3, col4 = st.columns(4)

with col1:
    winning_products = len(df[df['Rank'] == 1])
    st.metric(label="Prodotti Rank #1", value=f"{winning_products}", delta=f"{winning_products/len(df)*100:.0f}% del cat.")

with col2:
    critical_items = len(df[df['Status'] == "🔴 CRITICAL"])
    st.metric(label="Alert Critici", value=critical_items, delta="-2 vs ieri", delta_color="inverse")

with col3:
    avg_gap = df[df['Rank'] > 1]['Gap (€)'].mean()
    st.metric(label="Gap Medio (sui perdenti)", value=f"€ {avg_gap:.2f}", delta="Wait", delta_color="off")

with col4:
    potential_revenue = random.randint(500, 2000) # Fake metric
    st.metric(label="Revenue Opportunity", value=f"€ {potential_revenue}", delta="+12%")

st.markdown("---")

# 2. TABELLA PRINCIPALE
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Panoramica Prodotti")
    
    # Tabella interattiva
    event = st.dataframe(
        df_filtered.drop(columns=["object"]), # Nascondiamo l'oggetto tecnico
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn(
                "Status",
                help="Stato di allerta basato su Rank e Popolarità",
                width="medium",
            ),
            "Rank": st.column_config.NumberColumn(
                "Rank 🏆",
                format="%d",
            ),
            "Gap (€)": st.column_config.NumberColumn(
                "Gap",
                format="€ %.2f",
            ),
             "Mio Prezzo": st.column_config.NumberColumn(
                "Mio Prezzo",
                format="€ %.2f",
            ),
            "Min Mercato": st.column_config.NumberColumn(
                "Min Mercato",
                format="€ %.2f",
            ),
        },
        selection_mode="single-row",
        on_select="rerun"
    )

# 3. DETTAGLIO PRODOTTO (DRILL-DOWN)
with col_right:
    # Verifichiamo se l'utente ha selezionato una riga
    try:
        selection = event.selection.rows
        if selection:
            selected_index = selection[0]
            selected_row = df_filtered.iloc[selected_index]
            product_obj = selected_row["object"]
            
            st.subheader(f"🔍 Analisi: {product_obj.sku}")
            st.caption(selected_row["Prodotto"])
            
            # AI Insight Box
            st.markdown(f"""
            <div style="background-color: #e0e7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #4f46e5; margin-bottom: 20px;">
                <strong>🤖 AI Insight:</strong><br>
                {'Il competitor ' + selected_row['Competitor Top'] + ' ha abbassato il prezzo aggressivamente.' if selected_row['Status'] == '🔴 CRITICAL' else 'Posizionamento stabile. Mantieni il prezzo.'}
                <br><em>Suggerimento: {f"Abbassa a € {selected_row['Min Mercato'] - 0.10:.2f}" if selected_row['Status'] == '🔴 CRITICAL' else "Nessuna azione richiesta."}</em>
            </div>
            """, unsafe_allow_html=True)
            
            # Grafico Storico (Plotly)
            st.markdown("**Andamento 14 Giorni**")
            chart_data = generate_sparkline_data(selected_row["Min Mercato"], trend='down' if selected_row['Status'] == '🔴 CRITICAL' else 'stable')
            
            fig = px.line(chart_data, x="Data", y="Prezzo Mercato", markers=True)
            fig.add_hline(y=selected_row["Mio Prezzo"], line_dash="dash", line_color="red", annotation_text="Tuo Prezzo")
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=200,
                xaxis_title=None,
                yaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Info Competitor
            st.markdown("**Competitor Detail**")
            if product_obj.best_offers:
                for offer in product_obj.best_offers[:3]: # Mostra top 3
                    st.text(f"• {offer.merchant}: € {offer.price:.2f}")
            else:
                st.info("Nessun competitor rilevato.")

        else:
            st.info("👈 Seleziona un prodotto dalla tabella a sinistra per vedere i dettagli, i grafici e i suggerimenti AI.")
            
    except Exception as e:
        st.error(f"Errore nella visualizzazione dettagli: {e}")

# Footer
st.markdown("---")
st.caption("Developed with ❤️ using Streamlit & Python")
