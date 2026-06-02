import pytest
import sys
from pathlib import Path

# Add scripts to path so we can import them
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import run_stage0_01_occupancy
import run_stage0_02_hesitation
import run_stage0_03_dwell_time
import run_stage0_04_phantom
import run_stage0_05_noise

def test_scenario_1_occupancy():
    assert run_stage0_01_occupancy.run() is True

def test_scenario_2_hesitation():
    assert run_stage0_02_hesitation.run() is True

def test_scenario_3_dwell_time():
    assert run_stage0_03_dwell_time.run() is True

def test_scenario_4_phantom():
    assert run_stage0_04_phantom.run() is True

def test_scenario_5_noise():
    assert run_stage0_05_noise.run() is True
