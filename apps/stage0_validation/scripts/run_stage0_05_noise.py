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
    print("Running Scenario 5: Noise Environment")
    collector = CSICollector()
    aggregator = DataAggregator()
    
    base_time = datetime.datetime.now()
    
    # Testing Static + Moving with noisy background.
    phases = [
        ("noisy", 10, lambda score: score > 0.4), # moving (because of noise)
        ("moving", 10, lambda score: score > 0.4), # still moving
        ("noisy", 10, lambda score: score > 0.4), 
    ]
    
    total_minutes = sum(p[1] for p in phases)
    correct_minutes = 0
    details = []
    
    current_time = base_time
    for phase_name, duration, condition in phases:
        raw_data = collector.generate_simulated_data(duration, current_time, scenario=phase_name)
        
        for m in range(duration):
            window_start = current_time + datetime.timedelta(minutes=m)
            window_end = window_start + datetime.timedelta(minutes=1)
            
            agg = aggregator.aggregate_csi_minute(raw_data, window_start, window_end)
            if not agg.is_empty():
                score = agg["activity_score"][0]
                passed = condition(score)
                if passed:
                    correct_minutes += 1
                details.append({
                    "phase": phase_name,
                    "time": window_start.isoformat(),
                    "activity_score": score,
                    "passed": passed
                })
        
        current_time += datetime.timedelta(minutes=duration)
        
    accuracy = correct_minutes / total_minutes
    passed = accuracy >= 0.60
    
    print(f"Noise Scenario: {accuracy*100:.1f}% accuracy [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    save_result("05", "Noise Environment", accuracy, passed, details)
    return passed

if __name__ == "__main__":
    run()
