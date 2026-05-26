from typing import List, Dict, Any, Optional
import polars as pl

class Session:
    """Represents a single try-on session reconstructed from RFID and CSI data."""
    def __init__(self, store_id: str, fitting_room_id: int, rfid_events: List[Dict[str, Any]], csi_window: pl.DataFrame):
        self.store_id = store_id
        self.fitting_room_id = fitting_room_id
        self.rfid_events = rfid_events
        self.csi_window = csi_window
        
        # Calculate start and end times based on CSI window
        if not csi_window.is_empty():
            self.start_ms = csi_window["window_start_ms"].min()
            self.end_ms = csi_window["window_end_ms"].max()
            self.duration = (self.end_ms - self.start_ms) / 1000.0
        else:
            self.start_ms = 0
            self.end_ms = 0
            self.duration = 0.0

class JointSignals:
    """
    Implements the 5 core joint signals based on docs/planning/joint_signals_spec.md
    """
    
    @staticmethod
    def reconstruct_sessions(rfid_events: List[Dict[str, Any]], csi_windows: pl.DataFrame, store_id: str) -> List[Session]:
        """
        Reconstructs Try-on sessions by matching CSI occupancy windows with RFID events.
        Threshold: activity_score > 0.1 indicates occupancy.
        """
        sessions = []
        if csi_windows.is_empty():
            return sessions
            
        # Filter windows where activity_score > 0.1
        occupied = csi_windows.filter(pl.col("activity_score") > 0.1).sort("window_start_ms")
        
        if occupied.is_empty():
            return sessions
            
        # Simple grouping into continuous blocks (if gap > 3 mins, new session)
        blocks = []
        current_block = [occupied.row(0, named=True)]
        
        for i in range(1, len(occupied)):
            row = occupied.row(i, named=True)
            prev_row = current_block[-1]
            
            # 3 minutes gap (180_000 ms)
            if row["window_start_ms"] - prev_row["window_end_ms"] > 180_000:
                blocks.append(current_block)
                current_block = [row]
            else:
                current_block.append(row)
        blocks.append(current_block)
        
        # Create Session objects
        for block in blocks:
            block_df = pl.DataFrame(block)
            start_ms = block_df["window_start_ms"].min()
            end_ms = block_df["window_end_ms"].max()
            room_id = block_df["fitting_room_id"][0]
            
            # Find RFID events in this window
            session_rfid = [
                e for e in rfid_events 
                if e["fitting_room_id"] == room_id and start_ms <= e["timestamp_ms"] <= end_ms
            ]
            
            sessions.append(Session(store_id, room_id, session_rfid, block_df))
            
        return sessions

    @staticmethod
    def calculate_hesitation_score(session: Session) -> float:
        """
        Calculates Hesitation Score (0.0 to 1.0).
        High score = high hesitation.
        """
        if session.csi_window.is_empty() or not session.rfid_events:
            return 0.0
            
        # Count same category size changes
        categories = {}
        for event in session.rfid_events:
            if event["event_type"] == "enter":
                cat = event["metadata"].get("category", "unknown")
                size = event["metadata"].get("size", "unknown")
                if cat not in categories:
                    categories[cat] = set()
                categories[cat].add(size)
                
        size_swaps = sum(max(0, len(sizes) - 1) for sizes in categories.values())
        
        avg_activity = session.csi_window["activity_score"].mean()
        
        # Normalize size_swaps (max 5)
        norm_swaps = min(size_swaps / 5.0, 1.0)
        
        # Normalize duration (max 10 mins = 600 secs)
        duration_factor = min(session.duration / 600.0, 1.0)
        
        score = (0.4 * norm_swaps) + (0.3 * avg_activity) + (0.3 * duration_factor)
        return min(max(score, 0.0), 1.0)
        
    @staticmethod
    def detect_phantom(csi_windows: pl.DataFrame, rfid_events: List[Dict[str, Any]], threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Detects Phantom Try-ons (CSI occupancy but no RFID).
        """
        phantoms = []
        if csi_windows.is_empty():
            return phantoms
            
        # Group continuous CSI activity
        occupied = csi_windows.filter(pl.col("activity_score") > threshold).sort("window_start_ms")
        
        if occupied.is_empty():
            return phantoms
            
        current_block = [occupied.row(0, named=True)]
        for i in range(1, len(occupied)):
            row = occupied.row(i, named=True)
            prev_row = current_block[-1]
            if row["window_start_ms"] - prev_row["window_end_ms"] > 180_000:
                # Process block
                block_df = pl.DataFrame(current_block)
                start_ms = block_df["window_start_ms"].min()
                end_ms = block_df["window_end_ms"].max()
                duration = (end_ms - start_ms) / 1000.0
                
                if duration >= 60: # at least 1 minute
                    room_id = block_df["fitting_room_id"][0]
                    rfid_in_window = [
                        e for e in rfid_events 
                        if e["fitting_room_id"] == room_id and start_ms <= e["timestamp_ms"] <= end_ms
                    ]
                    if not rfid_in_window:
                        phantoms.append({
                            "fitting_room_id": room_id,
                            "timestamp_ms": start_ms,
                            "confidence": block_df["activity_score"].max()
                        })
                current_block = [row]
            else:
                current_block.append(row)
                
        # Process last block
        if current_block:
            block_df = pl.DataFrame(current_block)
            start_ms = block_df["window_start_ms"].min()
            end_ms = block_df["window_end_ms"].max()
            duration = (end_ms - start_ms) / 1000.0
            
            if duration >= 60:
                room_id = block_df["fitting_room_id"][0]
                rfid_in_window = [
                    e for e in rfid_events 
                    if e["fitting_room_id"] == room_id and start_ms <= e["timestamp_ms"] <= end_ms
                ]
                if not rfid_in_window:
                    phantoms.append({
                        "fitting_room_id": room_id,
                        "timestamp_ms": start_ms,
                        "confidence": block_df["activity_score"].max()
                    })
                    
        return phantoms
