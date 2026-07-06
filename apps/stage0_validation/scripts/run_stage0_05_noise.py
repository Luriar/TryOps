"""
시나리오 5: 노이즈 강건성 — v2: 센서별 열화 폭 비교.

🔴 시뮬레이션 기반 구조 검증. 실측은 하드웨어에서 (폰 WiFi/BT + 옆방 활동).
v2 변경: CSI/mmWave를 같은 노이즈 조건에 놓고 어느 쪽이 덜 무너지는지 비교
(concept_validation_spec v2 §2 — 산출물은 센서-신호 매핑표).
통과 기준: 조합 정확도 60%+ (v1 유지).
"""
import argparse
import json
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from stage0.csi_collector import CSICollector
from stage0.mmwave_collector import MmWaveCollector
from stage0.aggregator import DataAggregator


def save_result(scenario_num, name, accuracy, passed, details):
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"scenario_{scenario_num}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"scenario": name, "accuracy": accuracy, "passed": passed,
                   "details": details, "timestamp": timestamp}, f, indent=2, ensure_ascii=False)
    print(f"Result saved to {filename}")


def run(sensor: str = "both"):
    print(f"Running Scenario 5: Noise Environment [sensor={sensor}]")
    csi = CSICollector()
    mmw = MmWaveCollector()
    agg = DataAggregator()

    base_time = datetime.datetime.now()
    # 노이즈 환경에서 "사람 있음"을 유지 판정할 수 있는가
    phases = [("noisy", 10), ("moving", 10), ("noisy", 10)]
    total_minutes = sum(d for _, d in phases)

    per_sensor_correct = {"csi": 0, "mmwave": 0}
    combined_correct = 0
    details = []

    current_time = base_time
    for phase_name, duration in phases:
        csi_raw = csi.generate_simulated_data(duration, current_time, scenario=phase_name) if sensor in ("csi", "both") else None
        mmw_raw = mmw.generate_simulated_data(duration, current_time, scenario=phase_name) if sensor in ("mmwave", "both") else None

        for m in range(duration):
            ws = current_time + datetime.timedelta(minutes=m)
            we = ws + datetime.timedelta(minutes=1)
            minute_detail = {"phase": phase_name, "time": ws.isoformat()}
            csi_ok = mmw_ok = None

            if csi_raw is not None:
                a = agg.aggregate_csi_minute(csi_raw, ws, we)
                if not a.is_empty():
                    csi_ok = a.to_dicts()[0]["activity_score"] > 0.4
                    per_sensor_correct["csi"] += int(csi_ok)
                    minute_detail["csi_passed"] = csi_ok

            if mmw_raw is not None:
                a = agg.aggregate_mmwave_minute(mmw_raw, ws, we)
                if not a.is_empty():
                    mmw_ok = bool(a.to_dicts()[0]["presence"])
                    per_sensor_correct["mmwave"] += int(mmw_ok)
                    minute_detail["mmwave_passed"] = mmw_ok

            combined = any(x for x in (csi_ok, mmw_ok) if x is not None)
            combined_correct += int(combined)
            minute_detail["combined_passed"] = combined
            details.append(minute_detail)

        current_time += datetime.timedelta(minutes=duration)

    accuracy = combined_correct / total_minutes
    passed = accuracy >= 0.60

    if sensor in ("csi", "both"):
        print(f"  CSI 단독:    {per_sensor_correct['csi']/total_minutes*100:.1f}%")
    if sensor in ("mmwave", "both"):
        print(f"  mmWave 단독: {per_sensor_correct['mmwave']/total_minutes*100:.1f}%")
    print(f"Noise Scenario (combined): {accuracy*100:.1f}% [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")

    save_result("05", "Noise Environment", accuracy, passed, {
        "sensor_mode": sensor,
        "csi_accuracy": per_sensor_correct["csi"] / total_minutes,
        "mmwave_accuracy": per_sensor_correct["mmwave"] / total_minutes,
        "minutes": details,
    })
    return passed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sensor", choices=["csi", "mmwave", "both"], default="both")
    args = p.parse_args()
    run(sensor=args.sensor)
