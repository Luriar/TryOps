"""
RFID/POS 이벤트 합성기 — v2.

v2 변경 (joint_signals_spec.md v2 §1.1~1.2):
- epc 필드 추가: 개체 단위 가상 SGTIN. 세션-구매 3단 매칭(EPC 결정론 매칭)의 검증용.
- rssi 필드 추가: 인접 피팅룸 오독(Ghost-read) 필터 검증용.
- synthesize_pos_events(): 구매 이벤트에 동일 epc 전파 → 1단(EPC) 매칭 검증.
- inject_ghost_reads(): 인접 피팅룸 오독 케이스 의도적 주입 → Ghost-read 필터 검증.

🔴 가상 epc는 실제 SGTIN 인코딩 체계와 다를 수 있음 — Stage 1 실물 검증 (spec v2 §8).
"""
import polars as pl
import random
from typing import List, Dict, Any, Tuple


def make_epc(article_id: str, serial: int) -> str:
    """가상 SGTIN EPC 생성. 같은 article(SKU)이라도 개체마다 serial이 다르다."""
    return f"urn:epc:id:sgtin:8801234.{str(article_id).zfill(6)}.{serial:012d}"


class RFIDSynthesizer:
    """H&M Kaggle 데이터셋 기반 TryOps RFID/POS 이벤트 합성."""

    def __init__(self, hm_articles_path: str, hm_transactions_path: str):
        self.articles_path = hm_articles_path
        self.transactions_path = hm_transactions_path
        self._serial_counter = 0

    def _next_serial(self) -> int:
        self._serial_counter += 1
        return self._serial_counter

    def load_and_filter_data(self) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """H&M 데이터 로드 + 피팅 가능 카테고리 필터. 파일 없으면 목데이터."""
        try:
            articles = pl.read_csv(self.articles_path)
            transactions = pl.read_csv(self.transactions_path)
        except Exception:
            articles = pl.DataFrame({
                "article_id": ["001", "002", "003", "004", "005"],
                "garment_group_name": ["Jersey Basic", "Dresses Ladies", "Accessories", "Trousers", "Shoes"],
                "product_type_name": ["T-shirt", "Dress", "Bag", "Jeans", "Sneakers"],
                "colour_group_name": ["Black", "Red", "Black", "Blue", "White"],
            })
            transactions = pl.DataFrame({
                "t_dat": ["2026-05-22", "2026-05-22", "2026-05-22"],
                "customer_id": ["c1", "c1", "c2"],
                "article_id": ["001", "004", "002"],
                "price": [10.0, 30.0, 40.0],
            })

        fittable_groups = [
            "Jersey Basic", "Dresses Ladies", "Knitwear",
            "Trousers Denim", "Trousers", "Shirts", "Blouses",
            "Outdoor", "Skirts", "Sweaters",
        ]
        fittable_articles = articles.filter(pl.col("garment_group_name").is_in(fittable_groups))
        fittable_transactions = transactions.filter(
            pl.col("article_id").is_in(fittable_articles["article_id"].to_list())
        )
        return fittable_articles, fittable_transactions

    def synthesize_events(
        self,
        base_timestamp_ms: int,
        num_sessions: int = 10,
        hesitation_ratio: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """RFID enter/exit 이벤트 합성 (v2: epc·rssi 포함, exit도 동일 epc)."""
        articles, _ = self.load_and_filter_data()
        valid_articles = articles.to_dicts()
        if not valid_articles:
            return []

        events: List[Dict[str, Any]] = []
        current_time = base_timestamp_ms

        for _ in range(num_sessions):
            is_hesitation = random.random() < hesitation_ratio
            article = random.choice(valid_articles)
            epc = make_epc(article["article_id"], self._next_serial())

            events.append({
                "event_type": "enter",
                "fitting_room_id": 1,
                "epc": epc,
                "sku_id": article["article_id"],
                "timestamp_ms": current_time,
                "rssi": int(random.normalvariate(-50, 4)),
                "metadata": {
                    "category": article["garment_group_name"],
                    "size": "M",
                    "color": article["colour_group_name"],
                },
            })

            if is_hesitation:
                current_time += 60_000
                epc_l = make_epc(str(article["article_id"]) + "L", self._next_serial())
                events.append({
                    "event_type": "enter",
                    "fitting_room_id": 1,
                    "epc": epc_l,
                    "sku_id": str(article["article_id"]) + "_L",
                    "timestamp_ms": current_time,
                    "rssi": int(random.normalvariate(-50, 4)),
                    "metadata": {
                        "category": article["garment_group_name"],
                        "size": "L",
                        "color": article["colour_group_name"],
                    },
                })
                current_time += 180_000
            else:
                current_time += 120_000

            events.append({
                "event_type": "exit",
                "fitting_room_id": 1,
                "epc": epc,
                "sku_id": article["article_id"],
                "timestamp_ms": current_time,
                "rssi": int(random.normalvariate(-52, 4)),
                "metadata": {},
            })
            current_time += 300_000

        return events

    def synthesize_pos_events(
        self,
        rfid_events: List[Dict[str, Any]],
        conversion_ratio: float = 0.6,
        delay_ms_range: Tuple[int, int] = (5 * 60_000, 30 * 60_000),
    ) -> List[Dict[str, Any]]:
        """
        POS 결제 이벤트 합성 (v2 신규).
        입어본 개체(epc)의 conversion_ratio 만큼이 세션 후 5~30분 내 결제된다고 가정.
        → 3단 매칭의 1단(EPC 정확 매칭) 검증 데이터.
        """
        pos_events: List[Dict[str, Any]] = []
        enters = [e for e in rfid_events if e["event_type"] == "enter"]
        for i, e in enumerate(enters):
            if random.random() < conversion_ratio:
                pos_events.append({
                    "transaction_id": f"TXN_SIM_{i:04d}",
                    "timestamp_ms": e["timestamp_ms"] + random.randint(*delay_ms_range),
                    "items": [{
                        "epc": e["epc"],
                        "sku_id": e["sku_id"],
                        "quantity": 1,
                        "price": round(random.uniform(19000, 129000), -2),
                    }],
                    "payment_method": "card",
                })
        return pos_events

    @staticmethod
    def inject_ghost_reads(
        rfid_events: List[Dict[str, Any]],
        ghost_ratio: float = 0.15,
        adjacent_room_id: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        인접 피팅룸 오독(stray read) 주입 (v2 신규).
        일부 enter 이벤트를 복제해 옆 피팅룸(점유 없음)에서 낮은 RSSI로 읽힌 것처럼 만든다.
        → JointSignals.detect_ghost_reads() 필터 검증용.
        """
        ghosts: List[Dict[str, Any]] = []
        for e in rfid_events:
            if e["event_type"] == "enter" and random.random() < ghost_ratio:
                ghost = dict(e)
                ghost["fitting_room_id"] = adjacent_room_id
                ghost["rssi"] = int(random.normalvariate(-68, 3))  # 오독은 신호 약함
                ghost["metadata"] = dict(e.get("metadata", {}))
                ghosts.append(ghost)
        return rfid_events + ghosts
