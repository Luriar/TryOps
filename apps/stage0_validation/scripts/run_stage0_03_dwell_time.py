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
from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
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
    print("Running Scenario 3: Dwell Time")
    collector = CSICollector()
    aggregator = DataAggregator()
    
    base_time = datetime.datetime.now()
    
    # 4 phases: 2m short (static), 4m empty, 8m long (static), 2m empty
    phases = [
        ("static", 2),
        ("empty", 4),
        ("static", 8),
        ("empty", 2)
    ]
    
    csi_rows = []
    current_time = base_time
    for phase_name, duration in phases:
        raw_data = collector.generate_simulated_data(duration, current_time, scenario=phase_name)
        
        # 10 second aggregation for ±10s precision
        for s in range(0, duration * 60, 10):
            window_start = current_time + datetime.timedelta(seconds=s)
            window_end = window_start + datetime.timedelta(seconds=10)
            
            agg = aggregator.aggregate_csi_minute(raw_data, window_start, window_end)
            if not agg.is_empty():
                csi_rows.extend(agg.to_dicts())
        current_time += datetime.timedelta(minutes=duration)
        
    csi_windows = pl.DataFrame(csi_rows)
    sessions = JointSignals.reconstruct_sessions([], csi_windows, "store_1")
    
    if len(sessions) != 2:
        accuracy = 0.0
        passed = False
        details = {"error": f"Expected 2 sessions, got {len(sessions)}"}
    else:
        # Check durations
        durations = [s.duration for s in sessions]
        expected = [2*60, 8*60] # 120s and 480s
        correct = 0
        details = []
        for d, e in zip(durations, expected):
            is_accurate = abs(d - e) <= 25
            if is_accurate:
                correct += 1
            details.append({"expected": e, "actual": d, "passed": is_accurate})
            
        accuracy = correct / 2.0
        passed = accuracy >= 0.90
        
    print(f"Dwell Time Scenario: {accuracy*100:.1f}% accuracy [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    save_result("03", "Dwell Time", accuracy, passed, details)
    return passed

if __name__ == "__main__":
    run()
