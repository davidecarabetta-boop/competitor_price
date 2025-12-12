import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# Importiamo la logica dal core
from price_tracker_core import ProductRanking, get_mock_data, PriceIntelligenceEngine

# ==============================================================================
# CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Price Intelligence Hub",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Custom per replicare lo stile GfK/Minderest
st.markdown("""
<style>
    /* Global Font & Background */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Product Card (Left Panel) */
    .product-panel {
        background-color: white;
        padding: 24px;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        height: 100%;
    }
    .panel-label {
        font-size: 11px;
        color: #9ca3af;
        text-transform: uppercase;
        font-weight: 600;
        margin-top: 16px;
        margin-bottom: 4px;
    }
    .panel-value {
        font-size: 14px;
        color: #111827;
        font-weight: 500;
    }
    .panel-value-price {
        font-size: 20px;
        color: #1f2937;
        font-weight: bold;
    }
    
    /* Stock Badges */
    .stock-in {
        background-color: #d1fae5;
        color: #065f46;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .stock-out {
        background-color: #fef3c7; /* Giallo come nell'immagine */
        color: #92400e;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }

    /* Table Styling */
    .stDataFrame {
        border: 1px solid #e5e7eb;
        background-color: white;
    }
    
    /* Top Bar Styling */
    .top-bar {
        background-color: white;
        padding: 15px 20px;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATI & LOGICA
# ==============================================================================

def extract_brand(product_name):
    # Semplice euristica
    return product_name.split()[0]

def generate_history(base_price, variance=0.05):
    """Genera serie storica realistica"""
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
    """Prepara i dati nel formato esatto richiesto dalla UI target"""
    raw_data = get_mock_data()
    products = [ProductRanking(**item) for item in raw_data]
    analyzed_products = PriceIntelligenceEngine.enrich_data(products)
    
    ui_data = []
    for p in analyzed_products:
        brand = extract_brand(p.product_name)
        
        # Generiamo dati extra per matchare l'interfaccia
        mpn = f"{brand[:3].upper()}{random.randint(100,999)}XYZ"
        ean = f"{random.randint(1000000000000, 9999999999999)}"
        my_stock = "Out of stock" if random.random() > 0.7 else "In stock"
        
        # Storico Competitor
        history = {}
        # Noi (Retailer A - Blue)
        _, prices_me = generate_history(p.total_cost, 0.01)
        history["Noi"] = prices_me
        
        # Competitors (Retailer B, C - Colors)
        for i, offer in enumerate(p.best_offers[:4]):
            _, prices_comp = generate_history(offer.price, 0.03)
            history[offer.merchant] = prices_comp
            
        ui_data.append({
            "object": p,
            "id": p.sku,
            "brand": brand,
            "mpn": mpn,
            "ean": ean,
            "my_price": p.total_cost,
            "my_stock": my_stock,
            "category": p.category,
            "history_dates": _,
            "history_prices": history
        })
    
    return pd.DataFrame(ui_data)

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def render_left_panel(row):
    """Pannello laterale identico all'immagine"""
    # IMPORTANTE: Rimuoviamo l'indentazione interna per evitare che Markdown lo interpreti come 'Code Block'
    html_content = f"""
<div class="product-panel">
<div style="text-align: center; margin-bottom: 24px;">
<!-- Placeholder Immagine TV/Profumo -->
<img src="https://placehold.co/200x150/f3f4f6/a1a1aa?text=Product+Img" style="border-radius: 4px; width: 100%;">
</div>
<div class="panel-label">ID</div>
<div class="panel-value" style="color: #3b82f6;">{row['id']}</div>
<div class="panel-label">Brand</div>
<div class="panel-value" style="color: #3b82f6;">{row['brand']}</div>
<div class="panel-label">MPN</div>
<div class="panel-value" style="color: #3b82f6;">{row['mpn']}</div>
<div class="panel-label">EAN</div>
<div class="panel-value">{row['ean']}</div>
<div class="panel-label">Price</div>
<div class="panel-value-price">€ {row['my_price']:.2f}</div>
<div class="panel-label">Stock</div>
<span class="{ 'stock-in' if row['my_stock'] == 'In stock' else 'stock-out' }">
{row['my_stock']}
</span>
<div class="panel-label">Category</div>
<div style="background: #f3f4f6; padding: 2px 6px; display: inline-block; font-size: 12px; border-radius: 2px;">{row['category']}</div>
</div>
"""
    st.markdown(html_content, unsafe_allow_html=True)

def render_chart(row):
    """Grafico stile GfK: Linee tratteggiate e marker"""
    dates = row['history_dates']
    history = row['history_prices']
    
    fig = go.Figure()
    
    # Palette colori simile all'immagine (Blu scuro, Arancio, Rosso, Verde, Viola)
    colors = ['#1e40af', '#f97316', '#dc2626', '#16a34a', '#9333ea']
    symbols = ['circle', 'diamond', 'square', 'cross', 'x']
    
    for i, (merchant, prices) in enumerate(history.items()):
        is_me = merchant == "Sensation Profumerie"
        
        fig.add_trace(go.Scatter(
            x=dates, y=prices,
            mode='lines+markers',
            name=merchant,
            line=dict(
                color=colors[i % len(colors)], 
                width=2, 
                dash='solid' if is_me else 'dash' # Tratteggiato per gli altri
            ),
            marker=dict(symbol=symbols[i % len(symbols)], size=6)
        ))

    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f3f4f6', tickformat="%d %b"),
        yaxis=dict(showgrid=True, gridcolor='#f3f4f6'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_table(row):
    """Tabella Competitor dettagliata"""
    p_obj = row['object']
    
    table_data = []
    
    # Aggiungi Noi
    table_data.append({
        "Web": "🔵 Noi",
        "Product": row['object'].product_name,
        "Price": f"€ {row['my_price']}",
        "Diff": "-",
        "Stock": row['my_stock'],
        "Updated": datetime.now().strftime("%d-%m-%y %H:%M")
    })
    
    # Aggiungi Competitor
    for offer in p_obj.best_offers:
        diff_val = offer.price - row['my_price']
        diff_pct = (diff_val / row['my_price']) * 100
        color = "red" if diff_val < 0 else "green"
        
        stock_status = "In stock" if random.random() > 0.2 else "Out of stock"
        
        table_data.append({
            "Web": f"🔴 {offer.merchant}",
            "Product": row['object'].product_name, # Simuliamo link
            "Price": f"€ {offer.price:.2f}",
            "Diff": f"{diff_pct:+.1f}%", # Questo andrebbe colorato
            "Stock": stock_status,
            "Updated": (datetime.now() - timedelta(minutes=random.randint(10, 300))).strftime("%d-%m-%y %H:%M")
        })
        
    df_t = pd.DataFrame(table_data)
    
    # Render tabella custom
    st.dataframe(
        df_t,
        column_config={
            "Web": st.column_config.TextColumn("Web / Retailer", width="medium"),
            "Product": st.column_config.TextColumn("Product", width="large"),
            "Price": st.column_config.TextColumn("Price", width="small"),
            "Diff": st.column_config.TextColumn("Diff %", width="small"), # Streamlit base non supporta HTML nelle celle facilmente
            "Stock": st.column_config.TextColumn("Stock", width="small"),
            "Updated": st.column_config.TextColumn("Updated", width="medium"),
        },
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# MAIN APP
# ==============================================================================

# Header finto stile GfK
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/GfK_logo.svg/200px-GfK_logo.svg.png", width=60) # Logo placeholder
st.write("")

# Caricamento Dati
df = load_data_gfk_style()

# -- SIDEBAR RESTORED --
with st.sidebar:
    st.title("⚙️ Filtri & Config")
    st.text_input("🔑 API Key", type="password")
    st.divider()
    
    st.subheader("Filtra Prodotti")
    # Filtro Brand
    all_brands = sorted(df['brand'].unique())
    selected_brands = st.multiselect("Brand", all_brands, default=all_brands)
    
    # Filtro Categoria
    all_cats = sorted(df['category'].unique())
    selected_cats = st.multiselect("Category", all_cats, default=all_cats)
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Applicazione Filtri al DataFrame
df_filtered = df[df['brand'].isin(selected_brands) & df['category'].isin(selected_cats)]

if df_filtered.empty:
    st.error("Nessun prodotto trovato con i filtri correnti.")
    st.stop()

# Barra di ricerca in alto (usa df_filtered)
col_search, col_date_start, col_date_end, col_btn = st.columns([4, 1, 1, 1])
with col_search:
    # Dropdown che sembra una search bar
    product_list = df_filtered.apply(lambda x: f"{x['object'].product_name} (ID: {x['id']})", axis=1).tolist()
    # Gestione caso lista vuota post filtro
    if not product_list:
        st.warning("Nessun prodotto disponibile.")
        st.stop()
        
    selection = st.selectbox("Search products...", product_list, label_visibility="collapsed")
    
    # Trova l'indice corretto nel df filtrato
    selected_id_str = selection.split("(ID: ")[1].replace(")", "")
    selected_row = df_filtered[df_filtered['id'] == selected_id_str].iloc[0]

with col_date_start:
    st.date_input("Start", datetime.now() - timedelta(days=30), label_visibility="collapsed")
with col_date_end:
    st.date_input("End", datetime.now(), label_visibility="collapsed")
with col_btn:
    st.button("Apply", type="primary", use_container_width=True)

st.divider()

# Layout Principale
col_left, col_right = st.columns([1, 3])

with col_left:
    render_left_panel(selected_row)

with col_right:
    # Grafico
    render_chart(selected_row)
    
    st.write("")
    st.write("")
    
    # Controlli Tabella
    c1, c2 = st.columns([1, 5])
    with c1:
        st.selectbox("Display", ["3 records", "5 records", "All"], label_visibility="collapsed")
    with c2:
        st.text_input("Filter by text...", label_visibility="collapsed", placeholder="Filter by text...")

    # Tabella
    render_table(selected_row)
