"""
Stage 0 전체 실행 — v2: --sensor 인자 전달 + 센서별 정확도 요약.

통과 기준 (concept_validation_spec v2 §2):
  시나리오 1·2를 센서 조합으로 통과 + 5종 중 4종 통과.
"""
import argparse
import sys

import run_stage0_01_occupancy
import run_stage0_02_hesitation
import run_stage0_03_dwell_time
import run_stage0_04_phantom
import run_stage0_05_noise


def run_all(sensor: str = "both"):
    print(f"=== TryOps Stage 0 Validation (v2, sensor={sensor}) ===\n")
    results = [
        run_stage0_01_occupancy.run(sensor=sensor),
        run_stage0_02_hesitation.run(),                 # 목세션 기반, 센서 무관
        run_stage0_03_dwell_time.run(sensor=sensor),
        run_stage0_04_phantom.run(sensor=sensor),
        run_stage0_05_noise.run(sensor=sensor),
    ]

    passed_count = sum(results)
    print(f"\nFinal Result: {passed_count}/5 Scenarios Passed (Structure OK).")

    if passed_count >= 4 and results[0] and results[1]:
        print("Conclusion: STAGE 0 STRUCTURE_OK (HW 실측 필요). Proceed to Stage 1.")
        return 0
    else:
        print("Conclusion: STAGE 0 FAILED. Do not proceed to Stage 1.")
        return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sensor", choices=["csi", "mmwave", "both"], default="both",
                   help="검증에 사용할 센서 트랙 (기본: both = 병렬 비교)")
    args = p.parse_args()
    sys.exit(run_all(sensor=args.sensor))
