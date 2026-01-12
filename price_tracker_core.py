importimport os
import requests
import logging
import csv
import pandas as pd
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# Configurazione Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. MODELLI DATI (Pydantic)
# ==============================================================================

class BestOffer(BaseModel):
    price: float = Field(alias="Price")
    merchant: str = Field(alias="Merchant")
    rating: Optional[float] = Field(default=None, alias="Rating")

class ProductRanking(BaseModel):
    sku: str = Field(alias="Sku")
    brand: str = Field(default="N/A", alias="Brand") # Aggiunto Brand
    category: str = Field(alias="Category")
    product_name: str = Field(alias="Product")
    image_url: str = Field(default="", alias="ImageUrl") # Aggiunto per le immagini reali
    my_price: float = Field(alias="Price")
    shipping_cost: float = Field(alias="ShippingCost")
    total_cost: float = Field(alias="TotalCost")
    
    min_price_market: float = Field(alias="MinPrice")
    min_price_shipping_market: float = Field(alias="MinPriceWithShippingCost")
    rank: int = Field(alias="Rank")
    rank_with_shipping: int = Field(alias="RankWithShippingCost")
    
    competitors_count: int = Field(alias="NbMerchants")
    offers_count: int = Field(alias="NbOffers")
    popularity_index: int = Field(alias="Popularity")
    
    best_offers: List[BestOffer] = Field(default_factory=list, alias="BestOffers")
    timestamp: datetime = Field(default_factory=datetime.now)
    price_gap: Optional[float] = None
    is_winning: bool = False

    @field_validator('best_offers', mode='before')
    def parse_best_offers(cls, v):
        return v if v is not None else []

# ==============================================================================
# 2. ANALYTICS ENGINE
# ==============================================================================

class PriceIntelligenceEngine:
    @staticmethod
    def enrich_data(products: List[ProductRanking]) -> List[ProductRanking]:
        for p in products:
            p.is_winning = (p.rank_with_shipping == 1)
            gap = p.total_cost - p.min_price_shipping_market
            p.price_gap = round(gap, 2)
        return products

# ==============================================================================
# 3. GOOGLE SHEETS DATA FETCHING (Kaggle Format)
# ==============================================================================

def get_gsheet_data() -> List[Dict[str, Any]]:
    """Legge i dati dal Google Sheet con i nomi colonne Kaggle."""
    sheet_id = "1cnnxfowByYo6lwValEU_1YCT8ZQZO4mwSiwqeNx1wiA"
    gid = "797884028"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        logger.info("Connessione al dataset Kaggle su GSheet...")
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        
        products_list = []
        for i, row in df.iterrows():
            # Estrazione Prezzo (usa amountMax del dataset)
            try:
                price = float(row.get('prices.amountMax', 0))
            except:
                price = 0.0
            
            if price == 0: continue

            # Gestione Immagine (prende la prima della lista se presente)
            image_list = str(row.get('imageURLs', ''))
            image_url = image_list.split(',')[0] if image_list else "https://via.placeholder.com/150"

            # MAPPATURA COLONNE KAGGLE -> MODELLO INTERNO
            product_dict = {
                "Sku": str(row.get('id', row.get('asins', f'ID-{i}'))),
                "Brand": str(row.get('brand', 'Generic')),
                "Category": str(row.get('categories', 'Electronics')).split(',')[0],
                "Product": str(row.get('name', 'Product Name N/A')),
                "ImageUrl": image_url,
                "Price": price,
                "ShippingCost": 0.0,
                "TotalCost": price,
                "MinPrice": round(price * random.uniform(0.85, 0.98), 2),
                "MinPriceWithShippingCost": round(price * random.uniform(0.85, 0.98), 2),
                "Rank": random.randint(1, 8),
                "RankWithShippingCost": random.randint(1, 8),
                "NbMerchants": random.randint(1, 12),
                "NbOffers": random.randint(1, 15),
                "Popularity": random.randint(1, 100),
                "BestOffers": [
                    {"Price": round(price * 0.92, 2), "Merchant": "Amazon", "Rating": 4.8},
                    {"Price": round(price * 0.96, 2), "Merchant": "BestBuy", "Rating": 4.5},
                    {"Price": price, "Merchant": "Sensation Shop", "Rating": 4.9}
                ]
            }
            products_list.append(product_dict)
            
        return products_list
    except Exception as e:
        logger.error(f"Errore GSheet: {e}")
        return []

def get_mock_data():
    return get_gsheet_data()
