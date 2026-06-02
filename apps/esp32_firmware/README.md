# ESP32-S3 Firmware (TryOps Stage 0)

TryOps 매장의 피팅룸 모니터링을 위한 ESP32-S3 기반 센서 펌웨어입니다.

## 주요 기능
- WiFi를 통해 로컬 Store Gateway (Raspberry Pi 등)에 연결
- CSI (Channel State Information) 및 RSSI 데이터를 수집
- MQTT 프로토콜(`tryops/store/{id}/csi` 토픽)을 통해 10Hz 간격으로 데이터 전송

## 개발 환경 설정
- **PlatformIO** 권장 (VSCode 익스텐션)
- 보드: `esp32-s3-devkitc-1`
- 프레임워크: Arduino

## 의존성
- [PubSubClient](https://github.com/knolleary/pubsubclient): MQTT 통신
- [ArduinoJson](https://github.com/bblanchon/ArduinoJson): JSON 페이로드 구성

## 빌드 및 업로드 방법
1. `src/main.cpp`의 WiFi SSID, PW, 그리고 MQTT 게이트웨이 IP를 로컬 환경에 맞게 수정합니다.
2. PlatformIO에서 Build 및 Upload를 진행합니다.
