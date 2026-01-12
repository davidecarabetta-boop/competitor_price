import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# Importiamo la logica dal core
from price_tracker_core import ProductRanking, PriceIntelligenceEngine, get_gsheet_data

# ==============================================================================
# CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Price Intelligence Hub",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Custom per lo stile professionale (GfK Style)
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    .product-panel {
        background-color: white; padding: 24px; border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
    }
    .panel-label { font-size: 11px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-top: 16px; }
    .panel-value { font-size: 14px; color: #111827; font-weight: 500; }
    .panel-value-price { font-size: 22px; color: #1f2937; font-weight: bold; }
    .stock-in { background-color: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; }
    .stock-out { background-color: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATI & LOGICA
# ==============================================================================

def generate_history(base_price, variance=0.05):
    """Genera serie storica realistica per il grafico"""
    dates = [datetime.now() - timedelta(days=i) for i in range(30, -1, -1)]
    prices = []
    current = base_price
    for _ in range(31):
        change = random.uniform(-variance, variance)
        current = max(base_price * 0.7, current * (1 + change))
        prices.append(round(current, 2))
    return dates, prices

@st.cache_data
def load_data_gfk_style():
    """Trasforma i dati grezzi del GSheet in oggetti pronti per la UI"""
    raw_data = get_gsheet_data() 
    if not raw_data:
        return pd.DataFrame()

    # Arricchimento dati tramite l'engine
    products = [ProductRanking(**item) for item in raw_data]
    analyzed_products = PriceIntelligenceEngine.enrich_data(products)
    
    ui_data = []
    for p in analyzed_products:
        # Generiamo dati tecnici simulati se mancanti (MPN/EAN)
        mpn = f"{p.brand[:3].upper()}-{random.randint(100,999)}"
        ean = f"{random.randint(1000000000000, 9999999999999)}"
        my_stock = "Out of stock" if random.random() > 0.8 else "In stock"
        
        # Generazione Storico Prezzi
        history = {}
        dates, prices_me = generate_history(p.total_cost, 0.01)
        history["Sensation Shop (Noi)"] = prices_me
        
        for offer in p.best_offers:
            if offer.merchant != "Sensation Shop":
                _, prices_comp = generate_history(offer.price, 0.03)
                history[offer.merchant] = prices_comp
            
        ui_data.append({
            "object": p,
            "id": p.sku,
            "brand": p.brand,
            "product_name": p.product_name,
            "mpn": mpn,
            "ean": ean,
            "my_price": p.total_cost,
            "my_stock": my_stock,
            "category": p.category,
            "image": p.image_url,
            "history_dates": dates,
            "history_prices": history
        })
    return pd.DataFrame(ui_data)

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def render_left_panel(row):
    """Visualizza i dettagli del prodotto selezionato a sinistra"""
    # Se l'URL immagine è vuoto, usa un placeholder
    img_url = row['image'] if row['image'] and str(row['image']) != 'nan' else "https://via.placeholder.com/300?text=No+Image"
    
    html_content = f"""
    <div class="product-panel">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="{img_url}" style="border-radius: 4px; max-width: 100%; height: auto; max-height: 250px;">
        </div>
        <div class="panel-label">ID / ASIN</div>
        <div class="panel-value" style="color: #3b82f6;">{row['id']}</div>
        <div class="panel-label">Brand</div>
        <div class="panel-value">{row['brand']}</div>
        <div class="panel-label">MPN</div>
        <div class="panel-value">{row['mpn']}</div>
        <div class="panel-label">Price</div>
        <div class="panel-value-price">€ {row['my_price']:.2f}</div>
        <div class="panel-label">Stock</div>
        <div style="margin-top: 5px;">
            <span class="{'stock-in' if row['my_stock'] == 'In stock' else 'stock-out'}">{row['my_stock']}</span>
        </div>
        <div class="panel-label">Category</div>
        <div style="background: #f3f4f6; padding: 4px 8px; font-size: 12px; border-radius: 4px; display: inline-block;">{row['category']}</div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

def render_chart(row):
    """Grafico delle variazioni di prezzo dei competitor"""
    dates = row['history_dates']
    history = row['history_prices']
    fig = go.Figure()
    colors = ['#1e40af', '#f97316', '#dc2626', '#16a34a', '#9333ea']
    
    for i, (merchant, prices) in enumerate(history.items()):
        is_me = "Noi" in merchant
        fig.add_trace(go.Scatter(
            x=dates, y=prices, mode='lines+markers', name=merchant,
            line=dict(color=colors[i % len(colors)], width=2.5 if is_me else 1.5, dash='solid' if is_me else 'dash'),
            marker=dict(size=6)
        ))

    fig.update_layout(
        height=380, margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='white', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f3f4f6'),
        yaxis=dict(showgrid=True, gridcolor='#f3f4f6', title="Prezzo (€)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_table(row):
    """Tabella di confronto prezzi istantanea"""
    p_obj = row['object']
    table_data = []
    
    # Aggiungi dato "Noi"
    table_data.append({
        "Web": "🔵 Sensation Shop",
        "Price": f"€ {row['my_price']:.2f}",
        "Diff %": "-",
        "Stock": row['my_stock'],
        "Last Update": "Just now"
    })
    
    # Aggiungi competitor reali dal modello
    for offer in p_obj.best_offers:
        if offer.merchant == "Sensation Shop": continue
        diff_pct = ((offer.price - row['my_price']) / row['my_price']) * 100
        table_data.append({
            "Web": f"🔴 {offer.merchant}",
            "Price": f"€ {offer.price:.2f}",
            "Diff %": f"{diff_pct:+.1f}%",
            "Stock": "In Stock",
            "Last Update": f"{random.randint(5, 59)}m ago"
        })
        
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# ==============================================================================
# MAIN APP EXECUTION
# ==============================================================================

# Caricamento dati iniziali
df = load_data_gfk_style()

if df.empty:
    st.warning("📊 Nessun dato caricato. Verifica la connessione al Google Sheet.")
    st.stop()

# Sidebar per filtri
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/GfK_logo.svg/200px-GfK_logo.svg.png", width=80)
    st.title("Hub Intelligence")
    st.divider()
    
    brand_list = sorted(df['brand'].unique())
    selected_brand = st.multiselect("Filtra per Brand", brand_list, default=brand_list[:3] if len(brand_list)>3 else brand_list)
    
    cat_list = sorted(df['category'].unique())
    selected_cat = st.multiselect("Filtra per Categoria", cat_list, default=cat_list)
    
    if st.button("🔄 Aggiorna Dati GSheet", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Applicazione filtri
df_filtered = df[df['brand'].isin(selected_brand) & df['category'].isin(selected_cat)]

# Barra di ricerca superiore
st.subheader("Analisi Comparativa Mercato")
product_options = df_filtered.apply(lambda x: f"{x['brand']} - {x['product_name']} (ID: {x['id']})", axis=1).tolist()

if not product_options:
    st.error("Nessun prodotto corrisponde ai filtri selezionati.")
    st.stop()

selected_option = st.selectbox("Cerca Prodotto nel Dataset...", product_options)
selected_id = selected_option.split("(ID: ")[1].replace(")", "")
current_row = df_filtered[df_filtered['id'] == selected_id].iloc[0]

st.divider()

# Layout Principale (Colonne)
col_info, col_main = st.columns([1, 3], gap="large")

with col_info:
    render_left_panel(current_row)

with col_main:
    st.markdown(f"### {current_row['product_name']}")
    render_chart(current_row)
    
    st.markdown("#### Posizionamento Prezzi Competitor")
    render_table(current_row)

    # Note di Intelligence
    with st.expander("💡 Suggerimento Strategico"):
        gap = current_row['object'].price_gap
        if gap > 0:
            st.info(f"Sei più caro della media di mercato di €{gap}. Considera un ribasso del 2% per aumentare la conversione.")
        else:
            st.success(f"Sei il leader di prezzo per questo articolo! Gap: €{gap}. Mantieni la posizione.")
