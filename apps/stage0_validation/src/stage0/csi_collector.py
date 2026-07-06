"""
CSI 수집기 (ESP32-C6 + esp_wifi_sensing) — v2.

역할 (ADR-001): 대기구역·광역의 활동 강도(activity_score) 신호원.
알려진 한계: 모션 기반이므로 정지 인물은 빈 공간과 구분이 어렵다.
피팅룸 내부 재실 판정은 mmwave_collector가 담당한다.

구성:
- generate_simulated_data(): 하드웨어 없이 구조 검증
- read_realtime(): 실물 수신 — esp_wifi_sensing wifi_sensing_demo의
  웹 시리얼 프로토콜("HMS:" 접두 JSON 라인)을 파싱 (부품 도착 후)
두 경로 모두 동일한 DataFrame 스키마(rssi 프록시 컬럼)를 반환.
"""
import json
import time
import polars as pl
import numpy as np
from datetime import datetime, timedelta

HMS_PREFIX = "HMS:"


def parse_hms_line(line: str) -> dict | None:
    """
    esp_wifi_sensing 웹 시리얼 진단 라인 파싱.
    형식: "HMS:{...json...}" — 필드 예: jitter_value, smooth_scaled, state, init_stage
    (wifi_sensing_demo README 기준. 🔴 실기기에서 필드명 1회 검증 필요 — Week 1 G1)
    """
    line = line.strip()
    if not line.startswith(HMS_PREFIX):
        return None
    try:
        return json.loads(line[len(HMS_PREFIX):])
    except json.JSONDecodeError:
        return None


class CSICollector:
    """
    ESP32-C6 Serial Receiver & Simulator.
    v2: 대상 하드웨어 ESP32-S3 → ESP32-C6 (Espressif 공식 CSI 랭킹: C5 > C6 > S3).
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200,
                 fitting_room_id: int = 1):
        self.port = port
        self.baudrate = baudrate  # wifi_sensing_demo 기본 콘솔 속도
        self.fitting_room_id = fitting_room_id
        self._serial = None
        self.is_connected = False

    # ---------- 실물 연결 (부품 도착 후) ----------

    def connect(self) -> None:
        try:
            import serial  # pyserial
        except ImportError as e:
            raise RuntimeError("pip install pyserial 필요 (실물 연동 시)") from e
        self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        self.is_connected = True
        print(f"Connected to ESP32-C6 on {self.port} at {self.baudrate} baud.")

    def disconnect(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None
        self.is_connected = False
        print("Disconnected.")

    def send_command(self, cmd: str) -> None:
        """HMSCMD 명령 전송 (예: START_STREAM, RESET_BASELINE, GET_RUNTIME)."""
        if not self.is_connected:
            raise RuntimeError("connect() 먼저 호출")
        self._serial.write(f"HMSCMD {cmd}\n".encode())

    def read_realtime(self, duration_seconds: int, jitter_scale: float = 10.0) -> pl.DataFrame:
        """
        실물 수신: HMS 진단 라인을 duration 동안 수집해 rssi 프록시로 변환.

        jitter_value → rssi 프록시 매핑: rssi = -45 - (jitter_value / jitter_scale)
        기존 집계기(aggregate_csi_minute)가 rssi 표준편차 기반이므로,
        jitter의 변동이 그대로 activity_score로 이어진다.
        🔴 jitter_scale은 실측 캘리브레이션 대상 (Week 1~2).

        사용법 (부품 도착 후):
            c = CSICollector(port="COM3"); c.connect()
            c.send_command("START_STREAM")
            df = c.read_realtime(60)
        """
        if not self.is_connected:
            raise RuntimeError("connect() 먼저 호출")
        rows = []
        end = time.time() + duration_seconds
        while time.time() < end:
            raw = self._serial.readline().decode(errors="ignore")
            msg = parse_hms_line(raw)
            if msg is None or "jitter_value" not in msg:
                continue
            rows.append({
                "node_id": f"c6_{self.port}",
                "fitting_room_id": self.fitting_room_id,
                "timestamp_ms": int(time.time() * 1000),
                "rssi": -45.0 - float(msg["jitter_value"]) / jitter_scale,
            })
        return pl.DataFrame(rows)

    # ---------- 시뮬레이션 (하드웨어 없이) ----------

    def generate_simulated_data(
        self,
        duration_minutes: int,
        base_time: datetime,
        scenario: str = "empty"
    ) -> pl.DataFrame:
        """
        scenario: "empty", "static", "moving", "noisy"
        주의: "static"(정지 인물)의 요동은 빈 공간과 근소한 차이 —
              CSI의 본질적 한계를 시뮬레이션에도 반영 (시나리오 1에서 센서별 분리 채점하는 이유).
        """
        n_samples = duration_minutes * 60
        timestamps = [int((base_time + timedelta(seconds=i)).timestamp() * 1000) for i in range(n_samples)]

        if scenario == "empty":
            rssi = np.random.normal(-45, 0.5, n_samples)
        elif scenario == "static":
            rssi = np.random.normal(-50, 1.5, n_samples)
        elif scenario == "moving":
            rssi = np.random.normal(-55, 6.0, n_samples)
        elif scenario == "noisy":
            rssi = np.random.normal(-60, 10.0, n_samples)
        else:
            rssi = np.zeros(n_samples)

        return pl.DataFrame({
            "node_id": ["sim_node_1"] * n_samples,
            "fitting_room_id": [self.fitting_room_id] * n_samples,
            "timestamp_ms": timestamps,
            "rssi": rssi
        })
