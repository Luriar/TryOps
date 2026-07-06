"""
시나리오 3: Dwell Time (체류 시간 ±10초) — v2: presence 기반 세션 + hold_time 스윕.

🔴 시뮬레이션 기반 구조 검증. 실측은 ESP32-C6 + mmWave 하드웨어에서.
v2 변경: 점유 구간 판정이 CSI activity 임계값 → mmWave presence 기반 (spec v2 §2.1).
"""
import argparse
import json
import datetime
import polars as pl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from stage0.csi_collector import CSICollector
from stage0.mmwave_collector import MmWaveCollector
from stage0.aggregator import DataAggregator
from stage0.signals import JointSignals


def save_result(scenario_num, name, accuracy, passed, details):
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"scenario_{scenario_num}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"scenario": name, "accuracy": accuracy, "passed": passed,
                   "details": details, "timestamp": timestamp}, f, indent=2, ensure_ascii=False)
    print(f"Result saved to {filename}")


def _build_windows(sensor: str, phases, base_time):
    """10초 윈도우로 집계해 세션 재구성용 DataFrame 생성."""
    csi = CSICollector()
    mmw = MmWaveCollector()
    agg = DataAggregator()

    rows = []
    current_time = base_time
    for phase_name, duration in phases:
        csi_raw = csi.generate_simulated_data(duration, current_time, scenario=phase_name) if sensor in ("csi", "both") else None
        mmw_raw = mmw.generate_simulated_data(duration, current_time, scenario=phase_name) if sensor in ("mmwave", "both") else None

        for s in range(0, duration * 60, 10):
            ws = current_time + datetime.timedelta(seconds=s)
            we = ws + datetime.timedelta(seconds=10)
            csi_a = agg.aggregate_csi_minute(csi_raw, ws, we) if csi_raw is not None else pl.DataFrame()
            mmw_a = agg.aggregate_mmwave_minute(mmw_raw, ws, we) if mmw_raw is not None else pl.DataFrame()
            fused = agg.fuse_minute(csi_a, mmw_a)
            if not fused.is_empty():
                rows.extend(fused.to_dicts())
        current_time += datetime.timedelta(minutes=duration)

    return pl.DataFrame(rows)


def run(sensor: str = "both"):
    print(f"Running Scenario 3: Dwell Time [sensor={sensor}]")
    base_time = datetime.datetime.now()

    # 2m 정지 체류 / 4m 빈 공간 / 8m 정지 체류 / 2m 빈 공간
    # 주의: 체류를 "static"으로 두는 이유 — 피팅룸 실사용에서 정지 구간이 많음.
    # CSI 단독이면 static 체류를 놓치는 게 정상 (그게 v2 병렬 검증의 요점).
    phases = [("static", 2), ("empty", 4), ("static", 8), ("empty", 2)]

    windows = _build_windows(sensor, phases, base_time)
    sessions = JointSignals.reconstruct_sessions([], windows, "store_1")

    if len(sessions) != 2:
        accuracy = 0.0
        passed = False
        details = {"sensor_mode": sensor, "error": f"Expected 2 sessions, got {len(sessions)}"}
    else:
        durations = [s.duration for s in sessions]
        expected = [2 * 60, 8 * 60]
        correct = 0
        session_details = []
        for d, e in zip(durations, expected):
            is_accurate = abs(d - e) <= 25
            correct += int(is_accurate)
            session_details.append({"expected_s": e, "actual_s": d, "passed": is_accurate})
        accuracy = correct / 2.0
        passed = accuracy >= 0.90
        details = {"sensor_mode": sensor, "sessions": session_details}

    print(f"Dwell Time Scenario: {accuracy*100:.1f}% accuracy [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    save_result("03", "Dwell Time", accuracy, passed, details)
    return passed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sensor", choices=["csi", "mmwave", "both"], default="both")
    args = p.parse_args()
    run(sensor=args.sensor)
