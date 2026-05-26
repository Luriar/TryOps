import polars as pl
import random
from typing import List, Dict, Any, Tuple

class RFIDSynthesizer:
    """
    Synthesizes TryOps RFID events from H&M Kaggle Dataset.
    """
    
    def __init__(self, hm_articles_path: str, hm_transactions_path: str):
        self.articles_path = hm_articles_path
        self.transactions_path = hm_transactions_path

    def load_and_filter_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """
        Load H&M data and filter by clothing categories.
        If files are missing or in test environment, generates mock data.
        """
        try:
            articles = pl.read_csv(self.articles_path)
            transactions = pl.read_csv(self.transactions_path)
        except Exception:
            # Generate mock data for testing
            articles = pl.DataFrame({
                "article_id": ["001", "002", "003", "004", "005"],
                "garment_group_name": ["Jersey Basic", "Dresses Ladies", "Accessories", "Trousers", "Shoes"],
                "product_type_name": ["T-shirt", "Dress", "Bag", "Jeans", "Sneakers"],
                "colour_group_name": ["Black", "Red", "Black", "Blue", "White"]
            })
            transactions = pl.DataFrame({
                "t_dat": ["2026-05-22", "2026-05-22", "2026-05-22"],
                "customer_id": ["c1", "c1", "c2"],
                "article_id": ["001", "004", "002"],
                "price": [10.0, 30.0, 40.0]
            })

        fittable_groups = [
            "Jersey Basic", "Dresses Ladies", "Knitwear",
            "Trousers Denim", "Trousers", "Shirts", "Blouses",
            "Outdoor", "Skirts", "Sweaters"
        ]
        
        fittable_articles = articles.filter(
            pl.col("garment_group_name").is_in(fittable_groups)
        )
        
        fittable_transactions = transactions.filter(
            pl.col("article_id").is_in(fittable_articles["article_id"].to_list())
        )
        
        return fittable_articles, fittable_transactions

    def synthesize_events(self, base_timestamp_ms: int, num_sessions: int = 10, hesitation_ratio: float = 0.1) -> List[Dict[str, Any]]:
        """
        Synthesize RFID enter/exit events.
        """
        articles, _ = self.load_and_filter_data()
        valid_articles = articles.to_dicts()
        
        if not valid_articles:
            return []
            
        events = []
        current_time = base_timestamp_ms
        
        for i in range(num_sessions):
            # 10% chance of hesitation (multiple enters of same category, different size mock)
            is_hesitation = random.random() < hesitation_ratio
            
            article = random.choice(valid_articles)
            
            # First enter
            events.append({
                "event_type": "enter",
                "fitting_room_id": 1,
                "sku_id": article["article_id"],
                "timestamp_ms": current_time,
                "metadata": {
                    "category": article["garment_group_name"],
                    "size": "M", 
                    "color": article["colour_group_name"]
                }
            })
            
            if is_hesitation:
                current_time += 60_000 # 1 minute later
                events.append({
                    "event_type": "enter",
                    "fitting_room_id": 1,
                    "sku_id": article["article_id"] + "_L", # different size
                    "timestamp_ms": current_time,
                    "metadata": {
                        "category": article["garment_group_name"],
                        "size": "L",
                        "color": article["colour_group_name"]
                    }
                })
                current_time += 180_000 # 3 minutes testing
            else:
                current_time += 120_000 # 2 minutes testing
                
            # Exit
            events.append({
                "event_type": "exit",
                "fitting_room_id": 1,
                "sku_id": article["article_id"],
                "timestamp_ms": current_time,
                "metadata": {}
            })
            
            current_time += 300_000 # Next session in 5 mins
            
        return events
