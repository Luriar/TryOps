"""
Joint Signals — v2 (joint_signals_spec.md v2).

v2 변경:
- Session 재구성: activity_score 임계값 → presence 컬럼 우선 (mmWave 융합 윈도우 지원, CSI 폴백)
- match_sessions_to_pos(): 3단 신뢰도 매칭 (1단 EPC 결정론 > 2단 SKU 시간창 > 3단 집계)
- detect_ghost_reads(): 6번째 신호 — RFID 오독 필터 (Phantom의 역방향)
- detect_phantom(): presence 기반으로 트리거 교체
"""
from typing import List, Dict, Any, Optional
import polars as pl


def _occupied_windows(windows: pl.DataFrame, activity_threshold: float = 0.1) -> pl.DataFrame:
    """점유 윈도우 필터: presence 컬럼이 있으면(융합/mmWave) 그걸 쓰고, 없으면 CSI activity 폴백."""
    if "presence" in windows.columns:
        return windows.filter(pl.col("presence")).sort("window_start_ms")
    return windows.filter(pl.col("activity_score") > activity_threshold).sort("window_start_ms")


def _group_blocks(occupied: pl.DataFrame, gap_ms: int = 180_000) -> List[List[dict]]:
    """연속 점유 윈도우를 세션 블록으로 그룹화 (gap 초과 시 새 블록 = v1의 3분 규칙 유지)."""
    blocks: List[List[dict]] = []
    if occupied.is_empty():
        return blocks
    current = [occupied.row(0, named=True)]
    for i in range(1, len(occupied)):
        row = occupied.row(i, named=True)
        if row["window_start_ms"] - current[-1]["window_end_ms"] > gap_ms:
            blocks.append(current)
            current = [row]
        else:
            current.append(row)
    blocks.append(current)
    return blocks


class Session:
    """RFID + 점유 윈도우로 재구성된 단일 try-on 세션."""

    def __init__(self, store_id: str, fitting_room_id: int, rfid_events: List[Dict[str, Any]], csi_window: pl.DataFrame):
        self.store_id = store_id
        self.fitting_room_id = fitting_room_id
        self.rfid_events = rfid_events
        self.csi_window = csi_window  # v2: 융합 점유 윈도우 (이름은 호환성 유지)

        if not csi_window.is_empty():
            self.start_ms = csi_window["window_start_ms"].min()
            self.end_ms = csi_window["window_end_ms"].max()
            self.duration = (self.end_ms - self.start_ms) / 1000.0
        else:
            self.start_ms = 0
            self.end_ms = 0
            self.duration = 0.0

    @property
    def epcs(self) -> List[str]:
        """세션에서 enter된 EPC 목록 (v2)."""
        return [e["epc"] for e in self.rfid_events if e.get("event_type") == "enter" and "epc" in e]


class JointSignals:
    """Joint Signal 6종 (spec v2 §3)."""

    # ---------- Session 재구성 ----------

    @staticmethod
    def reconstruct_sessions(rfid_events: List[Dict[str, Any]], csi_windows: pl.DataFrame, store_id: str) -> List[Session]:
        """
        v2: presence 기반 점유 구간 (mmWave 우선), CSI-only 입력도 폴백 동작.
        RFID 이벤트는 detect_ghost_reads() 필터 후 넣는 것을 권장.
        """
        sessions: List[Session] = []
        if csi_windows.is_empty():
            return sessions

        occupied = _occupied_windows(csi_windows)
        for block in _group_blocks(occupied):
            block_df = pl.DataFrame(block)
            start_ms = block_df["window_start_ms"].min()
            end_ms = block_df["window_end_ms"].max()
            room_id = block_df["fitting_room_id"][0]
            session_rfid = [
                e for e in rfid_events
                if e["fitting_room_id"] == room_id and start_ms <= e["timestamp_ms"] <= end_ms
            ]
            sessions.append(Session(store_id, room_id, session_rfid, block_df))
        return sessions

    # ---------- 3단 매칭 (v2 신규) ----------

    @staticmethod
    def match_sessions_to_pos(
        sessions: List[Session],
        pos_events: List[Dict[str, Any]],
        sku_window_ms: int = 30 * 60_000,
    ) -> List[Dict[str, Any]]:
        """
        Session ↔ 구매 3단 신뢰도 매칭 (spec v2 §2.2).
        1단: EPC 정확 매칭 (결정론) — "입어본 바로 그 옷이 팔렸다"
        2단: 같은 SKU가 세션 종료 후 시간창 내 결제 (확률)
        3단: 미매칭 → SKU 집계 레벨에서만 유효
        반환: [{session, converted, match_tier, matched_epc/sku}]
        """
        pos_epcs: Dict[str, int] = {}
        pos_skus: List[tuple] = []  # (sku_id, timestamp_ms)
        for p in pos_events:
            for item in p.get("items", []):
                if item.get("epc"):
                    pos_epcs[item["epc"]] = p["timestamp_ms"]
                pos_skus.append((item.get("sku_id"), p["timestamp_ms"]))

        results = []
        for s in sessions:
            matched = None
            # 1단: EPC
            for epc in s.epcs:
                if epc in pos_epcs:
                    matched = {"converted": True, "match_tier": 1, "matched_epc": epc}
                    break
            # 2단: SKU 시간창
            if matched is None:
                session_skus = {e.get("sku_id") for e in s.rfid_events if e.get("event_type") == "enter"}
                for sku, ts in pos_skus:
                    if sku in session_skus and 0 <= ts - s.end_ms <= sku_window_ms:
                        matched = {"converted": True, "match_tier": 2, "matched_sku": sku}
                        break
            # 3단: 미매칭 (집계 레벨에서만 사용)
            if matched is None:
                matched = {"converted": False, "match_tier": 3}
            matched["session"] = s
            results.append(matched)
        return results

    # ---------- Hesitation (v1 유지, 입력만 융합 점수) ----------

    @staticmethod
    def calculate_hesitation_score(session: Session) -> float:
        if session.csi_window.is_empty() or not session.rfid_events:
            return 0.0

        categories: Dict[str, set] = {}
        for event in session.rfid_events:
            if event["event_type"] == "enter":
                cat = event["metadata"].get("category", "unknown")
                size = event["metadata"].get("size", "unknown")
                categories.setdefault(cat, set()).add(size)

        size_swaps = sum(max(0, len(sizes) - 1) for sizes in categories.values())
        avg_activity = session.csi_window["activity_score"].mean() if "activity_score" in session.csi_window.columns else 0.0
        norm_swaps = min(size_swaps / 5.0, 1.0)
        duration_factor = min(session.duration / 600.0, 1.0)

        score = (0.4 * norm_swaps) + (0.3 * (avg_activity or 0.0)) + (0.3 * duration_factor)
        return min(max(score, 0.0), 1.0)

    # ---------- Phantom (v2: presence 기반) ----------

    @staticmethod
    def detect_phantom(csi_windows: pl.DataFrame, rfid_events: List[Dict[str, Any]], threshold: float = 0.3) -> List[Dict[str, Any]]:
        """점유는 있는데 RFID 이벤트 없음 → RFID 누락 의심 (spec v2 §3.5: 60초+ 점유 기준)."""
        phantoms: List[Dict[str, Any]] = []
        if csi_windows.is_empty():
            return phantoms

        occupied = _occupied_windows(csi_windows, activity_threshold=threshold)
        for block in _group_blocks(occupied):
            block_df = pl.DataFrame(block)
            start_ms = block_df["window_start_ms"].min()
            end_ms = block_df["window_end_ms"].max()
            if (end_ms - start_ms) / 1000.0 < 60:
                continue
            room_id = block_df["fitting_room_id"][0]
            rfid_in_window = [
                e for e in rfid_events
                if e["fitting_room_id"] == room_id and start_ms <= e["timestamp_ms"] <= end_ms
            ]
            if not rfid_in_window:
                confidence = (
                    block_df["activity_score"].max()
                    if "activity_score" in block_df.columns else 1.0
                )
                phantoms.append({
                    "fitting_room_id": room_id,
                    "timestamp_ms": start_ms,
                    "confidence": confidence,
                })
        return phantoms

    # ---------- Ghost-read 필터 (v2 신규 — 6번째 신호) ----------

    @staticmethod
    def detect_ghost_reads(
        rfid_events: List[Dict[str, Any]],
        occupancy_windows: pl.DataFrame,
        tolerance_ms: int = 30_000,
        rssi_threshold: Optional[int] = -62,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Phantom의 역방향: RFID enter가 있는데 해당 피팅룸에 점유가 없음 → 인접 룸 오독 의심.
        RSSI가 임계값 이하이면 오독 확신도 상승 (spec v2 §3.6).
        반환: {"clean": [...], "ghosts": [...]}
        """
        clean: List[Dict[str, Any]] = []
        ghosts: List[Dict[str, Any]] = []

        if occupancy_windows.is_empty():
            return {"clean": list(rfid_events), "ghosts": []}

        for e in rfid_events:
            if e.get("event_type") != "enter":
                clean.append(e)
                continue
            room_windows = occupancy_windows.filter(
                (pl.col("fitting_room_id") == e["fitting_room_id"])
                & (pl.col("window_start_ms") <= e["timestamp_ms"] + tolerance_ms)
                & (pl.col("window_end_ms") >= e["timestamp_ms"] - tolerance_ms)
            )
            occupied = _occupied_windows(room_windows)
            is_ghost = occupied.is_empty()
            weak_rssi = rssi_threshold is not None and e.get("rssi", 0) <= rssi_threshold
            if is_ghost:
                g = dict(e)
                g["ghost_confidence"] = 0.9 if weak_rssi else 0.6
                ghosts.append(g)
            else:
                clean.append(e)
        return {"clean": clean, "ghosts": ghosts}
