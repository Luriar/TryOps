import polars as pl
import numpy as np
from datetime import datetime, timedelta

class CSICollector:
    """
    ESP32-S3 Serial Receiver (Skeleton) & Simulator.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 921600):
        self.port = port
        self.baudrate = baudrate
        self.is_connected = False

    def connect(self) -> None:
        """
        Connect to the ESP32-S3 serial port (Skeleton).
        """
        # In a real environment, use pyserial here
        self.is_connected = True
        print(f"Connected to ESP32-S3 on {self.port} at {self.baudrate} baud.")

    def disconnect(self) -> None:
        """
        Disconnect from the serial port.
        """
        self.is_connected = False
        print("Disconnected.")

    def generate_simulated_data(
        self, 
        duration_minutes: int, 
        base_time: datetime,
        scenario: str = "empty"
    ) -> pl.DataFrame:
        """
        Generate simulated CSI/RSSI data for testing without actual hardware.

        Args:
            duration_minutes: Total minutes of data to generate
            base_time: Start time of the simulation
            scenario: "empty", "static", "moving", or "noisy"

        Returns:
            pl.DataFrame: Simulated raw CSI dataframe (1 row per second for simplicity)
        """
        n_samples = duration_minutes * 60
        timestamps = [int((base_time + timedelta(seconds=i)).timestamp() * 1000) for i in range(n_samples)]
        
        # Base RSSI values depending on scenario
        if scenario == "empty":
            # Very stable RSSI
            rssi = np.random.normal(-45, 0.5, n_samples)
        elif scenario == "static":
            # Slightly fluctuating RSSI due to human body presence but still
            rssi = np.random.normal(-50, 1.5, n_samples)
        elif scenario == "moving":
            # Highly fluctuating RSSI
            rssi = np.random.normal(-55, 6.0, n_samples)
        elif scenario == "noisy":
            # Extreme noise
            rssi = np.random.normal(-60, 10.0, n_samples)
        else:
            rssi = np.zeros(n_samples)

        df = pl.DataFrame({
            "node_id": ["sim_node_1"] * n_samples,
            "fitting_room_id": [1] * n_samples,
            "timestamp_ms": timestamps,
            "rssi": rssi
        })
        
        return df
