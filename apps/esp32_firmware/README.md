# ESP32-S3 CSI 수집 센서 펌웨어

매장 내 배치된 ESP32-S3 개발 보드에서 실행되는 펌웨어입니다.

## 기능
- 특정 Wi-Fi 채널의 CSI(Channel State Information) 패킷 캡처
- 주변 고객의 움직임에 따른 신호 감쇄 및 위상 변화 수집
- 수집된 Raw CSI 프레임을 UDP 패킷으로 Store Gateway(Raspberry Pi)에 실시간 전송
