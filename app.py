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
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed" # Nascondiamo la sidebar per dare spazio alla UI principale
)

# Stile CSS per replicare il look "Clean" dell'immagine
st.markdown("""
<style>
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1f2937;
    }
    .metric-label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stock-badge-in {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .stock-badge-out {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    /* Forza bordo tabelle */
    .stDataFrame { border: 1px solid #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNZIONI DI SUPPORTO & MOCK AVANZATO
# ==============================================================================

def extract_brand(product_name):
    known_brands = ["Acqua di Parma", "Jean Paul Gaultier", "Yves Saint Laurent", "Dolce & Gabbana", "Chanel", "Dior", "Gucci"]
    for brand in known_brands:
        if product_name.lower().startswith(brand.lower()):
            return brand
    return product_name.split()[0]

def generate_competitor_history(base_price, competitor_name):
    """Genera una serie storica coerente per un competitor"""
    dates = [datetime.now() - timedelta(days=i) for i in range(30, -1, -1)]
    prices = []
    
    # Randomizziamo il comportamento del competitor (Aggressivo, Stabile, Caro)
    behavior = random.choice(['aggressive', 'stable', 'premium'])
    
    current_price = base_price * (0.95 if behavior == 'aggressive' else 1.05)
    
    for _ in range(31):
        change = random.uniform(-1.0, 1.0)
        if behavior == 'aggressive': change -= 0.05
        current_price += change
        prices.append(round(max(current_price, base_price * 0.7), 2))
        
    return dates, prices

@st.cache_data
def load_data_advanced():
    """Carica dati estesi per supportare la vista dettagliata"""
    raw_data = get_mock_data()
    products = [ProductRanking(**item) for item in raw_data]
    analyzed_products = PriceIntelligenceEngine.enrich_data(products)
    
    extended_data = []
    for p in analyzed_products:
        brand = extract_brand(p.product_name)
        
        # Simuliamo dati extra che non vengono dall'API ma servono per la UI "figa"
        mpn = f"{brand[:3].upper()}-{random.randint(1000, 9999)}"
        ean = f"{random.randint(1000000000000, 9999999999999)}"
        stock_status = "In Stock" if random.random() > 0.2 else "Out of Stock"
        
        # Simuliamo storico per 3 competitor fittizi + Noi
        competitors_history = {}
        # 1. Noi
        _, my_prices = generate_competitor_history(p.total_cost, "Noi")
        competitors_history["Noi"] = my_prices
        
        # 2. Competitor reali dall'API (Top 2)
        for offer in p.best_offers[:2]:
            _, prices = generate_competitor_history(offer.price, offer.merchant)
            competitors_history[offer.merchant] = prices
            
        # 3. Competitor Market Min (fittizio se serve)
        dates, min_prices = generate_competitor_history(p.min_price_shipping_market, "Market Min")

        extended_data.append({
            "SKU": p.sku,
            "Prodotto": p.product_name,
            "Brand": brand,
            "Categoria": p.category,
            "Mio Prezzo": p.total_cost,
            "Min Mercato": p.min_price_shipping_market,
            "Gap (€)": p.price_gap,
            "Rank": p.rank_with_shipping,
            "MPN": mpn,
            "EAN": ean,
            "Stock": stock_status,
            "History_Dates": dates,
            "History_Data": competitors_history,
            "BestOffers": p.best_offers,
            "object": p
        })
    
    return pd.DataFrame(extended_data)

# ==============================================================================
# UI COMPONENT: PRODUCT HEADER (LEFT COLUMN)
# ==============================================================================
def render_product_card(row):
    st.markdown(f"""
    <div class="product-card">
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
             <!-- Placeholder Immagine -->
            <div style="width: 200px; height: 200px; background-color: #f3f4f6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #9ca3af;">
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </div>
        </div>
        
        <div style="margin-bottom: 15px;">
            <div class="metric-label">ID</div>
            <div style="font-family: monospace; color: #4b5563;">{row['SKU']}</div>
        </div>
        
        <div style="margin-bottom: 15px;">
            <div class="metric-label">Brand</div>
            <div style="font-weight: 600;">{row['Brand']}</div>
        </div>

        <div style="margin-bottom: 15px;">
             <div class="metric-label">MPN / EAN</div>
             <div style="font-size: 12px; color: #4b5563;">{row['MPN']}<br>{row['EAN']}</div>
        </div>

        <hr style="margin: 20px 0; border: 0; border-top: 1px solid #e5e7eb;">

        <div style="margin-bottom: 15px;">
            <div class="metric-label">Il tuo Prezzo</div>
            <div class="metric-value">€ {row['Mio Prezzo']:.2f}</div>
        </div>

        <div style="margin-bottom: 15px;">
            <div class="metric-label">Stock Status</div>
            <span class="{ 'stock-badge-in' if row['Stock'] == 'In Stock' else 'stock-badge-out' }">
                {row['Stock']}
            </span>
        </div>
         <div style="margin-bottom: 15px;">
            <div class="metric-label">Categoria</div>
            <div style="font-size: 14px; color: #374151; background: #f3f4f6; padding: 2px 8px; border-radius: 12px; display: inline-block;">{row['Categoria']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# UI COMPONENT: CHART & TABLE (RIGHT COLUMN)
# ==============================================================================
def render_analysis_panel(row):
    # 1. FILTRI DATA (Visual)
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        st.date_input("Dal", datetime.now() - timedelta(days=30))
    with c2:
        st.date_input("Al", datetime.now())
    with c3:
        st.write("") # Spacer

    # 2. GRAFICO AVANZATO
    history_data = row['History_Data']
    dates = row['History_Dates']
    
    fig = go.Figure()
    
    # Aggiungi traccia per ogni competitor
    colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'] # Palette colori
    for i, (competitor, prices) in enumerate(history_data.items()):
        is_me = competitor == "Noi"
        line_style = dict(width=3) if is_me else dict(width=2, dash='dot')
        opacity = 1.0 if is_me else 0.7
        
        fig.add_trace(go.Scatter(
            x=dates, 
            y=prices,
            mode='lines+markers',
            name=competitor,
            line=line_style,
            marker=dict(size=6 if is_me else 4),
            opacity=opacity,
            line_color=colors[i % len(colors)]
        ))

    fig.update_layout(
        title="Trend Prezzi Competitor (30 Giorni)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f3f4f6'),
        hovermode="x unified",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. TABELLA COMPETITOR DETTAGLIATA
    st.subheader("Dettaglio Offerte Competitor")
    
    # Costruiamo i dati per la tabella
    comp_table_data = []
    
    # Aggiungiamo 'Noi'
    comp_table_data.append({
        "Retailer": "🔵 Noi",
        "Product": row['Prodotto'],
        "Price": row['Mio Prezzo'],
        "Diff %": 0.0,
        "Stock": row['Stock'],
        "Updated": datetime.now().strftime("%d-%m-%Y %H:%M")
    })
    
    # Aggiungiamo Competitor
    for offer in row['BestOffers']:
        diff_pct = ((offer.price - row['Mio Prezzo']) / row['Mio Prezzo']) * 100
        # Simuliamo stock competitor
        comp_stock = "In Stock" if random.random() > 0.1 else "Out of Stock"
        
        comp_table_data.append({
            "Retailer": f"🔴 {offer.merchant}",
            "Product": row['Prodotto'], # Spesso i nomi variano leggermente
            "Price": offer.price,
            "Diff %": diff_pct,
            "Stock": comp_stock,
            "Updated": (datetime.now() - timedelta(minutes=random.randint(5, 120))).strftime("%d-%m-%Y %H:%M")
        })
    
    df_comp = pd.DataFrame(comp_table_data)
    
    # Visualizzazione tabella custom
    st.dataframe(
        df_comp,
        column_config={
            "Retailer": st.column_config.TextColumn("Web / Retailer", width="medium"),
            "Product": st.column_config.TextColumn("Product Name", width="large"),
            "Price": st.column_config.NumberColumn("Price (€)", format="%.2f"),
            "Diff %": st.column_config.NumberColumn("Diff", format="%.1f%%"),
            "Stock": st.column_config.TextColumn("Stock"),
            "Updated": st.column_config.TextColumn("Updated"),
        },
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# MAIN APP LOGIC
# ==============================================================================

# Caricamento Dati
df = load_data_advanced()

# 1. BARRA DI RICERCA / SELEZIONE PRODOTTO (Top Bar)
st.title("Price Intelligence Hub")
col_search, col_kpi = st.columns([2, 1])

with col_search:
    # Creiamo un selettore che funge da "Ricerca"
    product_options = df.apply(lambda x: f"{x['SKU']} - {x['Prodotto']}", axis=1).tolist()
    selected_option = st.selectbox("🔎 Cerca Prodotto o Seleziona dalla lista:", product_options)
    
    # Estraiamo SKU selezionato
    selected_sku = selected_option.split(" - ")[0]
    selected_row = df[df['SKU'] == selected_sku].iloc[0]

with col_kpi:
    # Piccolo riassunto dello stato del prodotto selezionato
    rank = selected_row['Rank']
    color = "green" if rank == 1 else "red"
    st.markdown(f"""
    <div style="text-align: right; padding-top: 20px;">
        <span style="font-size: 14px; color: #6b7280;">Current Rank</span><br>
        <span style="font-size: 32px; font-weight: 800; color: {color};">#{rank}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# 2. LAYOUT MASTER (Split View come nell'immagine)
col_left, col_right = st.columns([1, 3]) # 25% Sinistra, 75% Destra

with col_left:
    render_product_card(selected_row)

with col_right:
    render_analysis_panel(selected_row)

st.caption("Developed with Ping Pong and Bruno")
