"""
시나리오 4: Phantom + Ghost-read 양방향 검증 — v2.

🔴 시뮬레이션 기반 구조 검증. 실측은 하드웨어에서.
v2 변경 (spec v2 §2, concept_validation_spec v2 §2):
- Phantom(점유 있음 + RFID 없음): v1 유지, presence 기반으로 트리거 교체
- Ghost-read(RFID 있음 + 점유 없음): 신규 — 인접 피팅룸 오독 필터 검증
- RFID 이벤트에 epc 포함 (rfid_synthesizer v2)
"""
import argparse
import json
import datetime
import polars as pl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from stage0.signals import JointSignals
from stage0.rfid_synthesizer import make_epc


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
    print(f"Running Scenario 4: Phantom + Ghost-read [sensor={sensor}]")
    now_ms = int(datetime.datetime.now().timestamp() * 1000)

    windows = []
    rfid_events = []
    expected_phantoms = []

    # --- Part A: Phantom (피팅룸 1: 10회 try-on, 2회 RFID 의도 누락) ---
    for i in range(10):
        start_ms = now_ms + i * 10 * 60 * 1000
        end_ms = start_ms + 5 * 60 * 1000
        windows.append({
            "fitting_room_id": 1,
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "activity_score": 0.8,
            "presence": True,
            "still_presence": False,
            "multi_occupancy_probability": 0.0,
        })
        if i in (3, 7):
            expected_phantoms.append(start_ms)
        else:
            rfid_events.append({
                "event_type": "enter",
                "timestamp_ms": start_ms + 1000,
                "fitting_room_id": 1,
                "epc": make_epc(f"{i:03d}", i),
                "sku_id": f"SKU_{i:03d}",
                "rssi": -50,
                "metadata": {"category": "Tshirt", "size": "M"},
            })

    windows_df = pl.DataFrame(windows)
    phantoms = JointSignals.detect_phantom(windows_df, rfid_events)
    detected_starts = [p["timestamp_ms"] for p in phantoms]
    phantom_correct = sum(1 for e in expected_phantoms if e in detected_starts)
    phantom_fp = len(detected_starts) - phantom_correct
    phantom_accuracy = phantom_correct / 2.0

    # --- Part B: Ghost-read (피팅룸 2: 점유 없음인데 오독 3건 주입) ---
    ghost_events = []
    for j in range(3):
        ts = now_ms + j * 15 * 60 * 1000 + 30_000
        ghost_events.append({
            "event_type": "enter",
            "timestamp_ms": ts,
            "fitting_room_id": 2,          # 점유 윈도우 없는 방
            "epc": make_epc(f"9{j:02d}", 900 + j),
            "sku_id": f"SKU_9{j:02d}",
            "rssi": -68,                    # 오독 특유의 약한 신호
            "metadata": {"category": "Tshirt", "size": "M"},
        })

    all_events = rfid_events + ghost_events
    filtered = JointSignals.detect_ghost_reads(all_events, windows_df)
    ghost_detected = len(filtered["ghosts"])
    # 정상 이벤트가 ghost로 오분류되지 않았는지
    clean_enters = [e for e in filtered["clean"] if e["event_type"] == "enter"]
    ghost_fp = len(rfid_events) - len(clean_enters)
    ghost_accuracy = min(ghost_detected, 3) / 3.0

    # --- 종합 ---
    accuracy = (phantom_accuracy + ghost_accuracy) / 2.0
    passed = phantom_accuracy >= 0.8 and phantom_fp == 0 and ghost_accuracy >= 0.8 and ghost_fp == 0

    details = {
        "sensor_mode": sensor,
        "phantom": {"expected": 2, "detected": len(phantoms), "false_positives": phantom_fp},
        "ghost_read": {"injected": 3, "detected": ghost_detected, "false_positives": ghost_fp},
    }

    print(f"  Phantom:    {phantom_accuracy*100:.1f}% (FP={phantom_fp})")
    print(f"  Ghost-read: {ghost_accuracy*100:.1f}% (FP={ghost_fp})")
    print(f"Phantom+Ghost Scenario: {accuracy*100:.1f}% [{'STRUCTURE_OK (HW 실측 필요)' if passed else 'FAIL'}]")
    save_result("04", "Phantom + Ghost-read Detection", accuracy, passed, details)
    return passed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sensor", choices=["csi", "mmwave", "both"], default="both")
    args = p.parse_args()
    run(sensor=args.sensor)
