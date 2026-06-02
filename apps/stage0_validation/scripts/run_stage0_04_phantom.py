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
from stage0.signals import JointSignals

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

def run():
    print("Running Scenario 4: Phantom Detection")
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    
    csi_rows = []
    rfid_events = []
    
    expected_phantoms = []
    
    # Generate 10 try-ons. Each is 5 mins long.
    for i in range(10):
        start_ms = now_ms + i * 10 * 60 * 1000
        end_ms = start_ms + 5 * 60 * 1000
        
        # High activity
        csi_rows.append({
            "fitting_room_id": 1,
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "activity_score": 0.8,
            "occupancy_estimate": 1,
            "movement_pattern": "active"
        })
        
        is_phantom = (i == 3 or i == 7) # 의도적으로 2번 누락
        if is_phantom:
            expected_phantoms.append(start_ms)
        else:
            rfid_events.append({
                "event_type": "enter",
                "timestamp_ms": start_ms + 1000,
                "fitting_room_id": 1,
                "metadata": {"category": "Tshirt", "size": "M"}
            })
            
    csi_windows = pl.DataFrame(csi_rows)
    phantoms = JointSignals.detect_phantom(csi_windows, rfid_events)
    
    detected_starts = [p["timestamp_ms"] for p in phantoms]
    
    correct = 0
    for e in expected_phantoms:
        if e in detected_starts:
            correct += 1
            
    # Also check false positives
    false_positives = len(detected_starts) - correct
    
    # total to detect = 2. 
    accuracy = correct / 2.0
    passed = accuracy >= 0.8 and false_positives == 0
    
    details = {
        "expected_count": 2,
        "detected_count": len(phantoms),
        "false_positives": false_positives
    }
    
    print(f"Phantom Detection Scenario: {accuracy*100:.1f}% accuracy [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    save_result("04", "Phantom Detection", accuracy, passed, details)
    return passed

if __name__ == "__main__":
    run()
