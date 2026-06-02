import sys
import run_stage0_01_occupancy
import run_stage0_02_hesitation
import run_stage0_03_dwell_time
import run_stage0_04_phantom
import run_stage0_05_noise

def run_all():
    print("=== TryOps Stage 0 Validation ===\n")
    results = [
        run_stage0_01_occupancy.run(),
        run_stage0_02_hesitation.run(),
        run_stage0_03_dwell_time.run(),
        run_stage0_04_phantom.run(),
        run_stage0_05_noise.run()
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
    sys.exit(run_all())
