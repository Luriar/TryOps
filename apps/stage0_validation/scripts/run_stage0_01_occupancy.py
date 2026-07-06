"""
시나리오 1: 점유 추정 (빈/정지/움직임) — v2: CSI/mmWave 병렬 채점.

🔴 본 스크립트는 시뮬레이션 데이터 기반 알고리즘 구조 검증.
실제 정확도는 ESP32-C6 + mmWave(LD2410C) 하드웨어 실측 후 확정.
concept_validation_spec.md v2 섹션 2: 정지 인물 구분을 센서별 분리 채점 —
CSI는 여기서 깨질 것으로 예상되며, mmWave가 커버하는지 확인하는 것이 목적.
통과 기준(v2): 센서 "조합" 정확도 80%+ (특정 센서 단독 통과 불필요).
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


# 페이즈별 정답 조건
CSI_CONDITIONS = {
    "empty": lambda w: w["activity_score"] < 0.1,
    "static": lambda w: 0.1 <= w["activity_score"] <= 0.4,   # CSI 약점 구간
    "moving": lambda w: w["activity_score"] > 0.4,
}
MMWAVE_CONDITIONS = {
    "empty": lambda w: not w["presence"],
    "static": lambda w: w["presence"] and w["still_presence"],  # mmWave 주특기
    "moving": lambda w: w["presence"] and not w["still_presence"],
}


def run(sensor: str = "both"):
    print(f"Running Scenario 1: Occupancy Detection [sensor={sensor}]")
    csi = CSICollector()
    mmw = MmWaveCollector()
    agg = DataAggregator()

    base_time = datetime.datetime.now()
    phases = [("empty", 10), ("static", 10), ("moving", 10), ("empty", 10)]
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
                    w = a.to_dicts()[0]
                    csi_ok = CSI_CONDITIONS[phase_name](w)
                    per_sensor_correct["csi"] += int(csi_ok)
                    minute_detail["csi_activity"] = round(w["activity_score"], 3)
                    minute_detail["csi_passed"] = csi_ok

            if mmw_raw is not None:
                a = agg.aggregate_mmwave_minute(mmw_raw, ws, we)
                if not a.is_empty():
                    w = a.to_dicts()[0]
                    mmw_ok = MMWAVE_CONDITIONS[phase_name](w)
                    per_sensor_correct["mmwave"] += int(mmw_ok)
                    minute_detail["mm_presence"] = w["presence"]
                    minute_detail["mm_still"] = w["still_presence"]
                    minute_detail["mmwave_passed"] = mmw_ok

            # 조합 채점: 선택된 센서 중 하나라도 맞으면 정답 (spec v2 통과 기준)
            combined = any(x for x in (csi_ok, mmw_ok) if x is not None)
            combined_correct += int(combined)
            minute_detail["combined_passed"] = combined
            details.append(minute_detail)

        current_time += datetime.timedelta(minutes=duration)

    accuracy = combined_correct / total_minutes
    passed = accuracy >= 0.80

    if sensor in ("csi", "both"):
        print(f"  CSI 단독:    {per_sensor_correct['csi']/total_minutes*100:.1f}%")
    if sensor in ("mmwave", "both"):
        print(f"  mmWave 단독: {per_sensor_correct['mmwave']/total_minutes*100:.1f}%")
    print(f"Occupancy Scenario (combined): {accuracy*100:.1f}% [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")

    save_result("01", "Occupancy Detection", accuracy, passed, {
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
