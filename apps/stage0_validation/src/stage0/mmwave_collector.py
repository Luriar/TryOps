"""
mmWave 수집기 (HLK-LD2410C / LD2450) — v2.

역할 (ADR-001):
- 피팅룸 내부의 재실(presence)·정지 재실(still)·다중 점유 가능성의 1차 센서.
- CSI(모션 기반)가 못 잡는 "정지 인물"을 커버한다.

구성:
- generate_simulated_data(): 하드웨어 없이 구조 검증 (Stage 0 사전 단계)
- read_realtime(): 실물 UART 수신 (부품 도착 후 — pyserial 필요)
두 경로 모두 동일한 DataFrame 스키마를 반환하므로 상위 로직 수정 불요.
"""
import time
import polars as pl
import numpy as np
from datetime import datetime, timedelta

# ---------- LD2410C UART 프로토콜 상수 ----------
LD2410_FRAME_HEADER = bytes([0xF4, 0xF3, 0xF2, 0xF1])
LD2410_FRAME_TAIL = bytes([0xF8, 0xF7, 0xF6, 0xF5])
# target_state: 0=없음, 1=움직임, 2=정지, 3=움직임+정지
LD2410_STATE_NONE, LD2410_STATE_MOVING, LD2410_STATE_STILL, LD2410_STATE_BOTH = 0, 1, 2, 3

# ---------- LD2450 UART 프로토콜 상수 ----------
LD2450_FRAME_HEADER = bytes([0xAA, 0xFF, 0x03, 0x00])
LD2450_FRAME_TAIL = bytes([0x55, 0xCC])


def parse_ld2410_frame(frame: bytes) -> dict:
    """
    LD2410C 기본 보고 프레임 파서.
    프레임 구조 (기본 모드):
      header(4) F4F3F2F1 | len(2, LE) | data_type(1)=0x02 | head(1)=0xAA
      | target_state(1) | moving_dist_cm(2, LE) | moving_energy(1)
      | still_dist_cm(2, LE) | still_energy(1) | detect_dist_cm(2, LE)
      | tail(1)=0x55 | check(1)=0x00 | frame_tail(4) F8F7F6F5
    🔴 오프셋은 제조사 매뉴얼 v1.03 기준 — Week 1 실기기에서 1회 검증 필요.
    """
    if not frame.startswith(LD2410_FRAME_HEADER):
        raise ValueError("Invalid LD2410 frame header")
    target_state = frame[8]
    return {
        "target_state": target_state,
        "presence": target_state != LD2410_STATE_NONE,
        "still": target_state in (LD2410_STATE_STILL, LD2410_STATE_BOTH),
        "moving_energy": frame[11],
        "still_energy": frame[14],
    }


def parse_ld2450_frame(frame: bytes) -> dict:
    """
    LD2450 타겟 추적 프레임 파서 (30바이트: header 4 + 타겟 3개 × 8 + tail 2).
    타겟 8바이트: x(2, LE, 부호형) | y(2) | speed(2) | dist_resolution(2)
    모든 필드 0 = 타겟 없음.
    """
    if not frame.startswith(LD2450_FRAME_HEADER):
        raise ValueError("Invalid LD2450 frame header")
    body = frame[4:28]
    count = 0
    for t in range(3):
        chunk = body[t * 8:(t + 1) * 8]
        if any(chunk):
            count += 1
    return {"target_count": count}


class MmWaveCollector:
    """HLK-LD2410C(재실/정지) + 선택적 LD2450(다중타겟) 수신기 & 시뮬레이터."""

    def __init__(self, port: str = "/dev/ttyUSB1", baudrate: int = 256000,
                 ld2450_port: str | None = None, fitting_room_id: int = 1):
        self.port = port
        self.baudrate = baudrate
        self.ld2450_port = ld2450_port  # LD2450 병행 시 별도 포트 (256000 baud)
        self.fitting_room_id = fitting_room_id
        self._serial = None
        self._serial_2450 = None
        self.is_connected = False

    # ---------- 실물 연결 (부품 도착 후) ----------

    def connect(self) -> None:
        try:
            import serial  # pyserial
        except ImportError as e:
            raise RuntimeError("pip install pyserial 필요 (실물 연동 시)") from e
        self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        if self.ld2450_port:
            self._serial_2450 = serial.Serial(self.ld2450_port, 256000, timeout=1)
        self.is_connected = True
        print(f"Connected: LD2410C on {self.port}"
              + (f", LD2450 on {self.ld2450_port}" if self.ld2450_port else ""))

    def disconnect(self) -> None:
        for s in (self._serial, self._serial_2450):
            if s is not None:
                s.close()
        self._serial = self._serial_2450 = None
        self.is_connected = False
        print("Disconnected.")

    def _read_one_ld2410(self) -> dict | None:
        """시리얼 스트림에서 프레임 동기화 후 1건 파싱."""
        buf = self._serial.read_until(LD2410_FRAME_TAIL, size=64)
        idx = buf.find(LD2410_FRAME_HEADER)
        if idx < 0 or len(buf) - idx < 19:
            return None
        try:
            return parse_ld2410_frame(buf[idx:])
        except (ValueError, IndexError):
            return None

    def _read_one_ld2450(self) -> dict | None:
        buf = self._serial_2450.read_until(LD2450_FRAME_TAIL, size=64)
        idx = buf.find(LD2450_FRAME_HEADER)
        if idx < 0 or len(buf) - idx < 30:
            return None
        try:
            return parse_ld2450_frame(buf[idx:])
        except (ValueError, IndexError):
            return None

    def read_realtime(self, duration_seconds: int) -> pl.DataFrame:
        """
        실물 수신: duration 동안 1초 1행 수집. 시뮬레이터와 동일 스키마 반환.
        사용법 (부품 도착 후):
            c = MmWaveCollector(port="COM4", ld2450_port="COM5"); c.connect()
            df = c.read_realtime(60)
        """
        if not self.is_connected:
            raise RuntimeError("connect() 먼저 호출")
        rows = []
        end = time.time() + duration_seconds
        while time.time() < end:
            second_start = time.time()
            r = self._read_one_ld2410()
            t_count = None
            if self._serial_2450 is not None:
                r2450 = self._read_one_ld2450()
                if r2450:
                    t_count = r2450["target_count"]
            if r:
                rows.append({
                    "node_id": f"mmwave_{self.port}",
                    "fitting_room_id": self.fitting_room_id,
                    "timestamp_ms": int(second_start * 1000),
                    "presence": r["presence"],
                    "still": r["still"],
                    "moving_energy": float(r["moving_energy"]),
                    "still_energy": float(r["still_energy"]),
                    "target_count": int(t_count if t_count is not None else (1 if r["presence"] else 0)),
                })
            # 1초 주기 유지
            remain = 1.0 - (time.time() - second_start)
            if remain > 0:
                time.sleep(remain)
        return pl.DataFrame(rows)

    # ---------- 시뮬레이션 (하드웨어 없이) ----------

    def generate_simulated_data(
        self,
        duration_minutes: int,
        base_time: datetime,
        scenario: str = "empty",
    ) -> pl.DataFrame:
        """
        scenario: "empty" | "static"(정지 인물 — CSI와의 결정적 차이) | "moving"
                  | "noisy" | "multi"(2인, LD2450 시뮬레이션)
        """
        n = duration_minutes * 60
        ts = [int((base_time + timedelta(seconds=i)).timestamp() * 1000) for i in range(n)]

        if scenario == "empty":
            presence = np.zeros(n, dtype=bool)
            still = np.zeros(n, dtype=bool)
            moving_energy = np.clip(np.random.normal(3, 2, n), 0, 100)
            still_energy = np.clip(np.random.normal(2, 1, n), 0, 100)
            targets = np.zeros(n, dtype=np.int32)
        elif scenario == "static":
            presence = np.random.random(n) > 0.02
            still = presence & (np.random.random(n) > 0.15)
            moving_energy = np.clip(np.random.normal(12, 6, n), 0, 100)
            still_energy = np.clip(np.random.normal(55, 10, n), 0, 100)
            targets = presence.astype(np.int32)
        elif scenario == "moving":
            presence = np.random.random(n) > 0.01
            still = np.zeros(n, dtype=bool)
            moving_energy = np.clip(np.random.normal(70, 15, n), 0, 100)
            still_energy = np.clip(np.random.normal(20, 8, n), 0, 100)
            targets = presence.astype(np.int32)
        elif scenario == "noisy":
            presence = np.random.random(n) > 0.05
            still = presence & (np.random.random(n) > 0.5)
            moving_energy = np.clip(np.random.normal(45, 25, n), 0, 100)
            still_energy = np.clip(np.random.normal(35, 20, n), 0, 100)
            targets = presence.astype(np.int32)
        elif scenario == "multi":
            presence = np.random.random(n) > 0.01
            still = presence & (np.random.random(n) > 0.6)
            moving_energy = np.clip(np.random.normal(60, 18, n), 0, 100)
            still_energy = np.clip(np.random.normal(45, 12, n), 0, 100)
            # LD2450 한계 반영: 근접 2인은 1타겟으로 병합될 수 있음 (ADR-001)
            targets = np.where(np.random.random(n) > 0.25, 2, 1).astype(np.int32)
            targets = np.where(presence, targets, 0)
        else:
            presence = np.zeros(n, dtype=bool)
            still = np.zeros(n, dtype=bool)
            moving_energy = np.zeros(n)
            still_energy = np.zeros(n)
            targets = np.zeros(n, dtype=np.int32)

        return pl.DataFrame({
            "node_id": ["mmwave_sim_1"] * n,
            "fitting_room_id": [self.fitting_room_id] * n,
            "timestamp_ms": ts,
            "presence": presence,
            "still": still,
            "moving_energy": moving_energy,
            "still_energy": still_energy,
            "target_count": targets,
        })
