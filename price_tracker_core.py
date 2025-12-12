import os
import requests
import logging
import csv
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

# Configurazione Logging Professionale
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. MODELLI DATI (Pydantic)
# Definiamo la struttura dati basandoci sul PDF Trovaprezzi
# ==============================================================================

class BestOffer(BaseModel):
    """Rappresenta un'offerta di un competitor nella Top 10"""
    price: float = Field(alias="Price")
    merchant: str = Field(alias="Merchant")
    rating: Optional[float] = Field(default=None, alias="Rating")

class ProductRanking(BaseModel):
    """
    Modello principale per i dati restituiti dall'API OffersRanking.
    Include validazione e pulizia dati automatica.
    """
    sku: str = Field(alias="Sku")
    category: str = Field(alias="Category")
    product_name: str = Field(alias="Product")
    my_price: float = Field(alias="Price")
    shipping_cost: float = Field(alias="ShippingCost")
    total_cost: float = Field(alias="TotalCost")
    
    # Dati Mercato
    min_price_market: float = Field(alias="MinPrice")
    min_price_shipping_market: float = Field(alias="MinPriceWithShippingCost")
    rank: int = Field(alias="Rank")
    rank_with_shipping: int = Field(alias="RankWithShippingCost")
    
    competitors_count: int = Field(alias="NbMerchants")
    offers_count: int = Field(alias="NbOffers")
    popularity_index: int = Field(alias="Popularity")
    
    # Lista delle migliori offerte (dettaglio competitor)
    best_offers: List[BestOffer] = Field(default_factory=list, alias="BestOffers")

    # Campi calcolati per la nostra Business Intelligence (non presenti nell'API)
    timestamp: datetime = Field(default_factory=datetime.now)
    price_gap: Optional[float] = None
    is_winning: bool = False

    @field_validator('best_offers', mode='before')
    def parse_best_offers(cls, v):
        # Gestisce il caso in cui l'API restituisca null o formati strani
        return v if v is not None else []

# ==============================================================================
# 2. CLIENT API TROVAPREZZI
# Implementazione della logica di fetch dati
# ==============================================================================

class TrovaprezziClient:
    BASE_URL = "https://services.7pixel.it/api/v1"

    def __init__(self, merchant_id: str, api_key: str):
        self.merchant_id = merchant_id
        self.api_key = api_key

    def _get_auth_token(self) -> str:
        """Richiede il token temporaneo."""
        endpoint = f"{self.BASE_URL}/TemporaryToken"
        params = {
            "merchantid": self.merchant_id,
            "merchantkey": self.api_key
        }
        
        try:
            logger.info("Richiesta nuovo token di autenticazione...")
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["Token"]
        except Exception as e:
            logger.error(f"Errore auth: {e}")
            raise

    def get_offers_ranking(self) -> List[ProductRanking]:
        """Scarica il ranking delle offerte."""
        try:
            token = self._get_auth_token()
            endpoint = f"{self.BASE_URL}/OffersRanking"
            params = {
                "merchantid": self.merchant_id,
                "token": token,
                "format": "json"
            }

            logger.info("Scaricamento dati OffersRanking...")
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            raw_data = response.json()
            return [ProductRanking(**item) for item in raw_data]

        except Exception as e:
            logger.error(f"Errore fetch dati: {e}")
            return []

# ==============================================================================
# 3. ANALYTICS ENGINE & MOCK DATA
# ==============================================================================

class PriceIntelligenceEngine:
    @staticmethod
    def enrich_data(products: List[ProductRanking]) -> List[ProductRanking]:
        """
        Aggiunge metriche calcolate: Gap di prezzo, Winning Status, ecc.
        """
        logger.info("Avvio analisi Price Intelligence...")
        
        for p in products:
            p.is_winning = (p.rank_with_shipping == 1)
            gap = p.total_cost - p.min_price_shipping_market
            p.price_gap = round(gap, 2)
            
            if not p.is_winning and p.popularity_index <= 3:
                logger.warning(f"ALERT: Perdita Rank su Top Seller '{p.product_name}'. Gap: €{p.price_gap}")

        return products

def get_mock_data() -> List[Dict[str, Any]]:
    """
    Restituisce dati simulati per testare l'applicazione senza chiamare l'API reale.
    Utile per lo sviluppo frontend e test AI.
    """
    return [
        {
            "Sku": "SKU1001A",
            "Category": "Profumi Donna",
            "Product": "Chanel Coco Mademoiselle EdP 100ml",
            "Price": 135.90,
            "ShippingCost": 0.0,
            "TotalCost": 135.90,
            "MinPrice": 134.90,
            "MinPriceWithShippingCost": 134.90,
            "Rank": 2,
            "RankWithShippingCost": 2,
            "NbMerchants": 5,
            "NbOffers": 5,
            "Popularity": 1,
            "BestOffers": [
                {"Price": 134.90, "Merchant": "ProfumoX", "Rating": 4.5},
                {"Price": 135.90, "Merchant": "Noi", "Rating": 4.8}
            ]
        },
        {
            "Sku": "SKU1002B",
            "Category": "Profumi Uomo",
            "Product": "Dior Sauvage EdT 60ml",
            "Price": 75.50,
            "ShippingCost": 4.90,
            "TotalCost": 80.40,
            "MinPrice": 75.50,
            "MinPriceWithShippingCost": 80.40,
            "Rank": 1,
            "RankWithShippingCost": 1,
            "NbMerchants": 3,
            "NbOffers": 3,
            "Popularity": 5,
            "BestOffers": [
                {"Price": 75.50, "Merchant": "Noi", "Rating": 4.8}
            ]
        },
        {
            "Sku": "SKU1003C",
            "Category": "Profumi Nicchia",
            "Product": "Acqua di Parma Fico di Amalfi 75ml",
            "Price": 89.99,
            "ShippingCost": 0.0,
            "TotalCost": 89.99,
            "MinPrice": 85.00,
            "MinPriceWithShippingCost": 85.00,
            "Rank": 7,
            "RankWithShippingCost": 7,
            "NbMerchants": 12,
            "NbOffers": 15,
            "Popularity": 55,
            "BestOffers": [
                {"Price": 85.00, "Merchant": "FragranzeTop", "Rating": 4.9},
                {"Price": 86.50, "Merchant": "ScontiProfumi", "Rating": 4.2}
            ]
        }
    ]

class DataExporter:
    @staticmethod
    def to_csv(products: List[ProductRanking], output_dir: str = "reports"):
        """Salva i dati su un file CSV formattato per Excel italiano (separatore ;)"""
        if not products:
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = f"report_prezzi_{datetime.now().strftime('%Y-%m-%d')}.csv"
        filepath = os.path.join(output_dir, filename)

        fieldnames = [
            "SKU", "Prodotto", "Categoria", "Mio Prezzo (Tot)", "Min Mercato (Tot)", 
            "Gap Prezzo", "Posizione (Rank)", "Vincitore?", "Popolarità"
        ]

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';', extrasaction='ignore')
                writer.writeheader()
                for p in products:
                    row = {
                        "SKU": p.sku,
                        "Prodotto": p.product_name,
                        "Categoria": p.category,
                        "Mio Prezzo (Tot)": str(p.total_cost).replace('.', ','),
                        "Min Mercato (Tot)": str(p.min_price_shipping_market).replace('.', ','),
                        "Gap Prezzo": str(p.price_gap).replace('.', ','),
                        "Posizione (Rank)": p.rank_with_shipping,
                        "Vincitore?": "SI" if p.is_winning else "NO",
                        "Popolarità": p.popularity_index
                    }
                    writer.writerow(row)
        except Exception as e:
            logger.error(f"Errore CSV: {e}")

if __name__ == "__main__":
    # Test Rapido
    products = [ProductRanking(**item) for item in get_mock_data()]
    analyzed = PriceIntelligenceEngine.enrich_data(products)
    print(f"Test completato. Analizzati {len(analyzed)} prodotti.")
