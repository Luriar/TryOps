"""
🔴 본 스크립트는 시뮬레이션 데이터 기반 알고리즘 구조 검증.
실제 정확도는 ESP32-S3 하드웨어 + 실제 피팅룸 환경 측정 후 확정.
concept_validation_spec.md 섹션 5.1 정량 기준은 HW 실측 시 적용.
"""
import os
import json
import datetime
import polars as pl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from stage0.signals import JointSignals, Session

def save_result(scenario_num, name, accuracy, passed, details):
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"scenario_{scenario_num}_{timestamp}.json"
    
    data = {
        "scenario": name,
        "accuracy": accuracy,
        "passed": passed,
        "details": details,
        "timestamp": timestamp
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Result saved to {filename}")

def mock_session(duration_mins, avg_activity, sizes_tried):
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    end_ms = now_ms + duration_mins * 60 * 1000
    
    # Mock CSI Window (just 1 row for simplicity that spans the duration)
    csi_window = pl.DataFrame({
        "fitting_room_id": [1],
        "window_start_ms": [now_ms],
        "window_end_ms": [end_ms],
        "activity_score": [avg_activity],
        "occupancy_estimate": [1],
        "movement_pattern": ["moderate"]
    })
    
    # Mock RFID events
    rfid_events = []
    for size in sizes_tried:
        rfid_events.append({
            "event_type": "enter",
            "timestamp_ms": now_ms + 1000,
            "fitting_room_id": 1,
            "metadata": {"category": "Tshirt", "size": size}
        })
        
    return Session("store_1", 1, rfid_events, csi_window)

def run():
    print("Running Scenario 2: Hesitation Pattern")
    
    # Pattern A: 3 mins, 1 size, moderate activity
    sess_a = mock_session(3, 0.3, ["M"])
    score_a = JointSignals.calculate_hesitation_score(sess_a)
    
    # Pattern B: 8 mins, 4 sizes, high activity (expect > 0.6)
    sess_b = mock_session(8, 0.8, ["S", "M", "L", "XL"])
    score_b = JointSignals.calculate_hesitation_score(sess_b)
    
    # Pattern C: 3 mins, 1 size, low activity
    sess_c = mock_session(3, 0.1, ["M"])
    score_c = JointSignals.calculate_hesitation_score(sess_c)
    
    passed_a = score_a < 0.4
    passed_b = score_b > 0.6
    passed_c = score_c < score_a
    
    correct = sum([passed_a, passed_b, passed_c])
    accuracy = correct / 3.0
    passed = accuracy >= 0.80
    
    details = [
        {"pattern": "A", "score": score_a, "passed": passed_a},
        {"pattern": "B", "score": score_b, "passed": passed_b},
        {"pattern": "C", "score": score_c, "passed": passed_c}
    ]
    
    print(f"Hesitation Scenario: {accuracy*100:.1f}% accuracy [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    print(f"Scores -> A: {score_a:.2f}, B: {score_b:.2f}, C: {score_c:.2f}")
    save_result("02", "Hesitation Pattern", accuracy, passed, details)
    return passed

if __name__ == "__main__":
    run()
