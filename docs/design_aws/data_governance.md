# Data Governance — 데이터 거버넌스 통합

> 본 문서는 TryOps 시스템의 데이터 거버넌스 통합 정책이다. 보존·삭제·분류·개인정보·감사 5영역.
>
> 기존 문서 분산 (`architecture.md` 섹션 6 + `legal_review.md`)을 한 곳에 통합 정리.
>
> 신뢰도 표기:
> - 🟢 한국 법규 직접 인용 + AWS 공식 가이드
> - 🟡 일반 거버넌스 원칙
> - 🔴 PoC 단계 검증 필요

---

## 0. 본 문서의 영역

1. **데이터 분류** (Classification) — 어떤 데이터가 어떤 등급인가
2. **보존 정책** (Retention) — 얼마나 보관하는가
3. **삭제 정책** (Deletion) — 어떻게 안전하게 삭제하는가
4. **개인정보 처리** (Privacy) — GDPR·개인정보보호법 대응
5. **감사** (Audit) — 누가 언제 무엇을 했는가 추적

---

## 1. 데이터 분류 (Classification)

### 1.1 분류 등급 5가지

| 등급 | 명칭 | 예시 | 처리 |
|---|---|---|---|
| L0 | Public | 회사 소개·서비스 안내 | 누구나 접근 |
| L1 | Internal | 매장 단위 익명 집계 | 본사·매장 접근 |
| L2 | Confidential | 본사 분석 결과 | 본사만 접근 |
| L3 | **Restricted** | 가명정보 (raw CSI + RFID + POS 결합) | 매장 게이트웨이 내부만 |
| L4 | **Personal** | 개인 식별 가능 (있다면) | 절대 수집·전송 안 함 |

### 1.2 데이터별 분류

| 데이터 | 위치 | 등급 | 근거 |
|---|---|---|---|
| 회사 소개 페이지 | Cloudflare | L0 | 공개 |
| 매장 메타데이터 | DynamoDB | L2 | 본사·매장 식별 |
| 매장 단위 시간 집계 | S3 mart | L1 | 익명 |
| Joint Signal 5종 결과 | S3 mart | L2 | 본사 분석 결과 |
| 본사 ROI 보고서 | S3 reports | L2 | 본사 비공개 |
| raw CSI 신호 | 매장 게이트웨이 SQLite (암호화) | L3 | 시간·매장 식별 가능 |
| RFID 이벤트 + POS 결합 | 매장 게이트웨이 SQLite | L3 | 가명정보 |
| POS 카드번호·전화번호 | (수집 안 함) | L4 | 매장 게이트웨이에서 제거 |
| CloudTrail 감사 로그 | 별도 격리 S3 | L2 | 보안 자산 |

🟢 **L4는 절대 AWS·본사로 전송 안 함**. 매장 게이트웨이에서 즉시 제거.

---

## 2. 보존 정책 (Retention)

### 2.1 보존 기간 표

| 데이터 | 위치 | 보존 기간 | 보존 사유 |
|---|---|---|---|
| 매장 게이트웨이 raw CSI | SQLCipher | **7일** | 재처리 + 장애 복구 |
| 매장 게이트웨이 1분 집계 | SQLCipher | 30일 | 매장 매니저 로컬 분석 |
| 매장 게이트웨이 RFID/POS | SQLCipher | 30일 | 동일 |
| AWS S3 raw (Firehose 적재) | S3 Standard → IA (90일+) | **90일** | 재처리 + 알고리즘 재학습 |
| AWS S3 mart (Joint Signal) | S3 Standard → IA (1년+) | **1년** | 본사 시즌 분석 |
| AWS S3 reports (월간 보고) | S3 Standard | **3년** | 본사 장기 추세 + 계약 의무 |
| 매장 메타데이터 | DynamoDB | 본사 계약 종료 + 30일 | 계약 보존 |
| 본사 사용자 인증 데이터 | Cognito | 사용자 삭제까지 | 사용자 통제 |
| CloudTrail 감사 로그 | S3 격리 + 암호화 | **1년** | 보안 의무 |
| 본사 권한 변경 로그 | RDS audit_logs | **1년** | 보안 의무 |
| 본사 액션 로그 (대시보드 사용) | RDS | 90일 | UX 분석 + 분쟁 대응 |

### 2.2 자동 정리 메커니즘

#### 매장 게이트웨이 (SQLite)

```python
# cron: 매일 자정
def cleanup_local_data():
    """매장 게이트웨이 SQLite 자동 정리."""
    
    seven_days_ago = now_ms() - 7 * 86400 * 1000
    thirty_days_ago = now_ms() - 30 * 86400 * 1000
    
    # raw CSI 7일 후 삭제
    sqlite.execute("DELETE FROM raw_csi WHERE timestamp_ms < ?", [seven_days_ago])
    
    # 1분 집계·RFID·POS 30일 후 삭제
    sqlite.execute("DELETE FROM csi_aggregates WHERE window_start_ms < ?", [thirty_days_ago])
    sqlite.execute("DELETE FROM rfid_events WHERE timestamp_ms < ?", [thirty_days_ago])
    sqlite.execute("DELETE FROM pos_events WHERE timestamp_ms < ?", [thirty_days_ago])
    
    # VACUUM (디스크 공간 회수)
    sqlite.execute("VACUUM")
```

#### AWS S3 (Lifecycle Policy)

```yaml
S3 Lifecycle Rules:
  - Id: raw_archive
    Prefix: raw/
    Status: Enabled
    Transitions:
      - Days: 90
        StorageClass: STANDARD_IA
      - Days: 180
        StorageClass: GLACIER_INSTANT_RETRIEVAL
    Expiration:
      Days: 365  # 1년 후 완전 삭제
  
  - Id: mart_archive
    Prefix: mart/
    Status: Enabled
    Transitions:
      - Days: 365
        StorageClass: STANDARD_IA
    Expiration:
      Days: 1095  # 3년 후 삭제
  
  - Id: reports_keep
    Prefix: reports/
    Status: Enabled
    Expiration:
      Days: 1095  # 3년
```

🟢 S3 IA $0.0125/GB-month (Standard $0.023 대비 46% 절감).

#### DynamoDB · RDS

- DynamoDB: TTL 속성 활용 (자동 삭제)
- RDS: 매일 자정 cron으로 오래된 로그 삭제

### 2.3 보존 정책 정정 가능성

본 정책은 **본사 계약 시 조정 가능**:

```yaml
본사별 보존 정책 옵션 (계약):
  - Standard: 위 표 그대로
  - Extended: raw 1년·mart 3년 (본사 추가 비용)
  - Compliance: GDPR·개인정보보호법 강화 (raw 30일·mart 1년)
```

본사가 *"5년치 트렌드 분석"* 요구 시 reports만 5년 연장 가능 (비용 추가).

---

## 3. 삭제 정책 (Deletion)

### 3.1 삭제 시나리오 4가지

#### 시나리오 1: 본사 계약 종료

```yaml
계약 종료 + 30일 grace period:
  Day 0: 본사 통지
  Day 1~30: 본사가 데이터 export 가능
  Day 30: 모든 본사 데이터 *"논리적 삭제"* (브랜드 KMS 키 폐기)
  Day 90: 물리적 삭제 (S3 객체 완전 제거)
  Day 365: 백업 데이터까지 완전 삭제
```

KMS 키 폐기로 *"논리적 삭제"* 즉시 가능:
- S3 객체는 남아있지만 키 없이는 복호화 불가
- GDPR Article 17 (Right to be Forgotten) 만족

#### 시나리오 2: 매장 도입 철회

```yaml
매장 철회:
  Day 0: 매장 게이트웨이 회수
  Day 0: 게이트웨이 Remote Wipe (SQLCipher 키 + 데이터)
  Day 7: 본사 S3에서 해당 매장 데이터 익명화
  Day 90: 매장 메타데이터 완전 삭제
```

#### 시나리오 3: 손님 개인정보 처리 정지 요청

```yaml
손님이 본사에 처리 정지 요청:
  - 본사 → TryOps 통보
  - 매장 단위 익명 데이터라 개인 식별 불가 (검색 못 함)
  - 본사 안내문: "본 매장은 카메라·녹음·개인 식별 없이 매장 혼잡도만 익명으로 측정합니다"
  - 손님이 *"매장 출입 거부"* 또는 *"본사 데이터 처리 거부"* 가능
```

#### 시나리오 4: 보안 인시던트 데이터 격리

```yaml
유출 의심 데이터:
  Day 0: 해당 데이터 즉시 격리 (별도 bucket)
  Day 1: 한국인터넷진흥원 신고 (24시간 의무)
  Day 30: 영향 평가 + 본사 통보
  Day 90: 격리 데이터 삭제 (법적 분쟁 종료 후)
```

### 3.2 삭제 검증

```python
def verify_deletion(brand_id):
    """본사 데이터 삭제 검증."""
    
    checks = {
        "s3_raw_objects": count_s3_objects(f"raw/brand_id={brand_id}/") == 0,
        "s3_mart_objects": count_s3_objects(f"mart/brand_id={brand_id}/") == 0,
        "dynamodb_metadata": query_dynamodb(brand_id) is None,
        "cognito_users": count_cognito_users(brand_id) == 0,
        "kms_key_status": get_kms_key_status(brand_id) == "PendingDeletion",
        "backup_replicas": count_backup_replicas(brand_id) == 0
    }
    
    if all(checks.values()):
        return True
    else:
        log_error("Deletion incomplete", checks)
        return False
```

삭제 완료 후 본사에 *"삭제 완료 증명서"* 발송.

---

## 4. 개인정보 처리 (Privacy)

### 4.1 한국 개인정보보호법 매핑

`legal_review.md` 섹션 1·2·3과 통합:

| 법규 조항 | TryOps 대응 |
|---|---|
| 제25조 영상정보처리기기 | 🟢 WiFi CSI는 영상 아님, 면제 |
| 제15조 수집·이용 동의 | 🟢 매장 안내문 + 본사 개인정보처리방침 |
| 제17조 제공 동의 | 🟢 본사 ↔ TryOps 위탁 계약 |
| 제28조의2 가명정보 | 🟢 매장 게이트웨이 raw는 가명, AWS는 익명 |
| 제35조 열람 요구 | 🟡 매장 단위 익명이라 개인 검색 불가 |
| 제36조 정정·삭제 | 🟡 동일 |
| 제37조 처리정지 | 🟢 매장 출입 거부 또는 본사 데이터 처리 거부 |

### 4.2 GDPR 매핑 (글로벌 확장 시)

| GDPR Article | TryOps 대응 |
|---|---|
| Art. 6 Lawful basis | 본사와 위탁 계약 + 매장 안내문 |
| Art. 7 Consent | 동의 필요 시 본사 통한 동의 |
| Art. 15 Right to Access | 손님이 매장 안내문 확인 가능 |
| Art. 17 Right to Erasure | KMS 키 폐기로 즉시 삭제 |
| Art. 25 Privacy by Design | 매장 게이트웨이에서 익명화 |
| Art. 32 Security | `security_design.md` 참조 |
| Art. 33 Breach notification | 24시간 내 본사·당국 통보 |
| Art. 35 DPIA | 본 문서가 DPIA 골격 |

### 4.3 Data Processing Agreement (DPA)

본사 ↔ TryOps 계약에 포함할 DPA 핵심 조항:

```markdown
1. 처리 목적: 매장 운영 효율 분석
2. 처리 항목: 매장 단위 익명 집계 (개인 식별 없음)
3. 처리 기간: 본사 계약 기간 + 90일
4. 처리 방법: 자동 시스템 (수동 처리 없음)
5. 보안 조치: security_design.md 전체
6. 위탁 재위탁 금지: 본사 사전 동의 없이 제3자 위탁 금지
7. 본사 권리: 데이터 export 권리, 처리 정지 권리, 삭제 권리
8. 손해배상: 유출·법규 위반 시 손해 배상 책임 분담
9. 분쟁 해결: 한국 서울중앙지방법원 전속 관할
```

🔴 본 DPA 골격은 한국 법무법인 검토 필수.

### 4.4 개인정보 영향평가 (DPIA)

```yaml
DPIA 자동화:
  Trigger: 새 데이터 유형 추가 또는 처리 방법 변경
  
  체크리스트:
    - [ ] L4 (Personal) 데이터 수집 여부
    - [ ] 새 데이터의 분류 등급 결정
    - [ ] 보존 기간 정의
    - [ ] 삭제 메커니즘 검증
    - [ ] 본사 통보 필요 여부
    - [ ] DPA 업데이트 필요 여부
  
  결과: data_governance.md v2 갱신
```

---

## 5. 감사 (Audit)

### 5.1 감사 대상 (Auditable Events)

```yaml
시스템 액션:
  - AWS API 호출 (모두) → CloudTrail
  - S3 객체 접근 → S3 Access Logs
  - Cognito 인증·인증 거부 → Cognito Logs

사용자 액션:
  - 본사 대시보드 로그인·로그아웃
  - 권한 변경 (role 변경, store_ids 변경)
  - 데이터 export
  - 본사 사용자 추가·삭제
  - 본사 계약 변경

데이터 액션:
  - 데이터 export
  - KMS 키 폐기 (계약 종료)
  - 보존 정책 변경
  - 삭제 검증 결과
```

### 5.2 감사 로그 스키마

```json
{
  "timestamp": "2026-05-22T15:30:45+09:00",
  "actor_type": "user|system|admin",
  "actor_id": "user_001@brand_001.com",
  "actor_ip": "121.xxx.xxx.xxx",
  "action": "role_change",
  "target_type": "user",
  "target_id": "user_002@brand_001.com",
  "before_state": {"role": "viewer"},
  "after_state": {"role": "merchandiser"},
  "metadata": {
    "brand_id": "brand_001",
    "approver": "user_admin@brand_001.com",
    "trace_id": "abc-123"
  }
}
```

### 5.3 감사 리포트

```yaml
정기 감사 리포트:
  주간:
    - 권한 변경 요약
    - 데이터 export 활동
    - 보안 알람 발생
  
  월간:
    - 본사별 사용자 활동
    - 데이터 보존 정책 준수율
    - 비정상 액세스 패턴
  
  연간:
    - 외부 감사 (KISA) 준비 자료
    - DPIA 갱신
    - DPA 검토
```

### 5.4 감사 자료 보존

| 자료 | 보존 |
|---|---|
| CloudTrail 로그 | 1년 (KMS 암호화) |
| 사용자 액션 로그 | 1년 |
| 권한 변경 로그 | 영구 (별도 격리) |
| 감사 리포트 (월간) | 5년 |
| 외부 감사 결과 | 영구 |

---

## 6. 데이터 export

본사가 *"본인 데이터 다운로드"* 요청 시 응답.

### 6.1 Export 기능

```yaml
본사 대시보드 → "데이터 export":
  옵션:
    - 기간 선택 (최근 1년 / 3년 / 전체)
    - 형식 선택 (CSV / Parquet / JSON)
    - 포함 데이터 (raw / mart / reports / all)
  
  처리:
    - Lambda가 비동기 작업 시작
    - 사용자에게 *"준비 완료 시 이메일 전송"*
    - S3 presigned URL 생성 (24시간 유효)
    - 본사 이메일로 다운로드 링크
```

### 6.2 Export 형식

```yaml
CSV: 단순 분석용
Parquet: 본사 자체 BI 도구 통합용
JSON: API 통합용

압축:
  - 1GB 미만: 그대로
  - 1GB+: gzip 또는 zip
```

### 6.3 Export 감사

모든 export는 감사 로그에 기록:
- 누가 (사용자 ID)
- 언제
- 어떤 데이터 (기간·범위)
- 어떤 형식
- 다운로드 IP

---

## 7. 데이터 품질 (Quality)

### 7.1 데이터 품질 KPI

```yaml
완전성 (Completeness):
  - 매장 게이트웨이 → AWS 전송 성공률: >99.5%
  - 일별 ETL 완료율: >99%

정확성 (Accuracy):
  - RFID-CSI session matching 정확도: >90%
  - Joint Signal 신뢰도 (PoC 검증 후 측정)

시의성 (Timeliness):
  - 실시간 알람 latency: <5분
  - 본사 일별 보고: 다음 날 오전 9시 이전

일관성 (Consistency):
  - 본사 대시보드 vs S3 raw 데이터 일치성: 100%
  - 매장 게이트웨이 ↔ AWS 데이터 일치성: 100%
```

### 7.2 데이터 품질 모니터링

```python
# 일별 데이터 품질 체크
def daily_quality_check():
    """매일 자정 데이터 품질 검증."""
    
    for store_id in active_stores():
        # 어제 데이터 적재 확인
        yesterday_data = check_s3_data(store_id, yesterday())
        
        if not yesterday_data:
            alert(f"Missing data: {store_id} {yesterday()}")
        
        # Joint Signal 결과 검증
        signals = check_joint_signals(store_id, yesterday())
        if not signals_valid(signals):
            alert(f"Invalid signals: {store_id}")
    
    # 본사별 보고서 생성 확인
    for brand_id in active_brands():
        if not daily_report_exists(brand_id, yesterday()):
            alert(f"Missing report: {brand_id}")
```

---

## 8. 거버넌스 운영 체크리스트

### 8.1 일간

- [ ] 데이터 품질 KPI 검증
- [ ] 비정상 액세스 패턴 점검
- [ ] CloudTrail 알람 점검

### 8.2 주간

- [ ] 권한 변경 로그 검토
- [ ] 보안 인시던트 후속 조치 점검
- [ ] 본사별 데이터 사용량 모니터링

### 8.3 월간

- [ ] 보존 정책 준수율 검증 (자동화 결과)
- [ ] 본사 사용자 활동 분석
- [ ] 데이터 export 활동 검토
- [ ] 비용 vs 데이터 보존 정책 정합성

### 8.4 분기

- [ ] 권한 전체 감사
- [ ] DPIA 갱신
- [ ] DPA 검토
- [ ] 내부 보안 감사

### 8.5 연간

- [ ] 외부 감사 (KISA · 한국정보보호산업협회)
- [ ] DR 훈련
- [ ] 데이터 거버넌스 정책 v2 업데이트
- [ ] 본사별 SLA 리포트 발송

---

## 9. 본 거버넌스 v1의 한계

본 v1은:
- 🔴 실제 본사 계약 0건, DPA 검증 미진행
- 🔴 한국 법무법인 정식 검토 미진행
- 🔴 데이터 분류 정확성 미검증 (실제 데이터 없음)
- 🔴 보존 정책의 비용 영향 정밀 미산출
- 🔴 GDPR 글로벌 확장 시 정밀화 부재

**진짜 사업 시작 시**: 첫 본사 계약 시점에 DPA 한국 법무법인 검토. KISA 외부 감사 1년 1회 실시.

**본 문서 활용 가이드**: 본사 보안·법무 검토 시 본 문서 + `security_design.md` + `legal_review.md` 3종 패키지 제출. DPA 협상 자료로 활용.
