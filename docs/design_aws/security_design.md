# Security Design — 보안 위협 모델링 및 대응

> 본 문서는 `architecture.md` 섹션 6 보안 설계의 상세 자료다. TryOps 시스템의 4가지 보안 위협 + 대응 + 멀티테넌트 격리 + 컴플라이언스 통합 설계.
>
> **본 문서의 한계**: 보안 설계는 *"진짜 위협이 새로 나타날 때"* 정밀화되는 영역. 본 v1은 위협 모델링 + 일반 대응의 골격. 진짜 사업 시 보안 감사 (KISA 보안성 평가 등) 통과 검증 필수.
>
> 신뢰도 표기:
> - 🟢 AWS 공식 보안 가이드 + 한국 법규 직접 인용
> - 🟡 일반 보안 원칙 + 합리적 추정
> - 🔴 위협 추측, PoC 단계 보안 감사로 검증 필요

---

## 0. 본 문서가 답하는 질문

- TryOps 시스템에 어떤 보안 위협이 있는가?
- 각 위협을 어떻게 차단하는가?
- 본사간 데이터 격리는 어떻게 보장하는가?
- 매장 게이트웨이 도난 시 어떻게 대응하는가?
- 보안 감사·법무 검토 시 무엇을 제출하는가?

---

## 1. 보안 위협 모델 (STRIDE 기반)

STRIDE: Spoofing · Tampering · Repudiation · Information Disclosure · Denial of Service · Elevation of Privilege

### 1.1 위협 우선순위 매트릭스

| 위협 ID | 종류 | 자산 | 발생 가능성 | 임팩트 | 우선순위 |
|---|---|---|---|---|---|
| T-1 | Information Disclosure | 매장 게이트웨이 데이터 | 🔴 높음 | 매우 높음 | **P0** |
| T-2 | Spoofing | ESP32-S3 노드 펌웨어 | 🟡 중간 | 높음 | **P1** |
| T-3 | Elevation of Privilege | 본사 대시보드 권한 | 🟡 중간 | 매우 높음 | **P0** |
| T-4 | Tampering | AWS S3 데이터 격리 | 🔴 낮음 | 매우 높음 | **P1** |
| T-5 | DoS | API Gateway · Lambda | 🟡 중간 | 중간 | P2 |
| T-6 | Repudiation | 본사 액션 로그 | 🟡 낮음 | 중간 | P2 |

본 문서는 P0·P1 위협 (T-1·T-2·T-3·T-4) 중심으로 대응 정의.

---

## 2. 위협 T-1: 매장 게이트웨이 도난·해킹 (P0)

### 2.1 위협 시나리오

매장에 두는 Raspberry Pi 4B 게이트웨이가:
- 절도로 가져가짐
- 매장 직원이 무단 접속·데이터 추출
- 매장 인터넷을 통해 외부 공격자가 SSH 접속

도난 시 잠재 손실:
- 7일치 SQLite raw 데이터 (CSI·RFID·POS)
- 본사 API 키
- 매장 식별자 + 본사 식별자
- ESP32-S3 노드 페어링 정보

### 2.2 대응 7가지

#### 대응 1: SQLite 암호화 (SQLCipher)

```python
import sqlcipher3 as sqlite3

# 매장 게이트웨이 SQLite 생성 시
conn = sqlite3.connect("tryops.db")
conn.execute(f"PRAGMA key = '{STORE_LOCAL_KEY}'")  # 매장당 고유 키
```

- 🟢 SQLCipher: AES-256 암호화, 오픈소스, 무료
- 도난 시 디스크 마운트해도 데이터 읽을 수 없음
- 매장 게이트웨이 부팅 시 본사 KMS에서 키 가져오기 (네트워크 필요)

#### 대응 2: API 키 회전 (Rotation)

```yaml
매장 게이트웨이 API 키 정책:
  - 발급: 매장 게이트웨이 등록 시 본사 KMS에서 발급
  - 보관: AWS Systems Manager Parameter Store SecureString
  - 회전: 90일 자동 회전
  - 즉시 폐기: 도난 보고 시 본사 대시보드에서 1-click 폐기
```

#### 대응 3: 매장 게이트웨이 위치 추적

```python
# 매장 게이트웨이가 1분마다 본사에 heartbeat 송신
{
  "store_id": "store_001",
  "device_id": "gateway_abc123",
  "external_ip": "121.xxx.xxx.xxx",  # 매장 인터넷 IP
  "timestamp": "...",
  "device_fingerprint": "..."  # 하드웨어 시리얼·MAC 등
}
```

- IP 변경 감지 시 알람 (매장 인터넷 변경 vs 도난)
- device_fingerprint 변경 시 즉시 차단

#### 대응 4: SSH 비활성화 + Wireguard VPN 전용 접근

- 매장 게이트웨이 SSH 외부 노출 차단
- 본사 SRE 접근은 Wireguard VPN 전용
- 매장 인터넷 → VPN 게이트웨이 → 매장 게이트웨이

#### 대응 5: 매장 직원 물리 접근 차단

- 매장 게이트웨이를 *"건드릴 수 없는 위치"* 에 설치 (천장 · 매장 잠금실)
- 매장 도입 시 본사·매장 매니저·TryOps 3자 합의서
- 게이트웨이 케이스에 탬퍼 라벨 (Tamper-Evident Seal)

#### 대응 6: 자동 데이터 소거 (Remote Wipe)

```python
# 본사 대시보드에서 도난 보고 시
def remote_wipe(store_id, device_id):
    """매장 게이트웨이 원격 데이터 소거."""
    
    # 1. API 키 즉시 폐기 (다음 heartbeat에서 거부)
    revoke_api_key(device_id)
    
    # 2. 매장 게이트웨이가 heartbeat 거부 응답 받으면
    #    자체적으로 SQLite 삭제 + 부팅 디스크 포맷
    
    # 3. 본사 대시보드에 *"매장 데이터 소거 완료"* 알림
    notify_brand(store_id, "remote_wipe_complete")
```

🟡 위 로직은 게이트웨이가 인터넷 연결됐을 때만. 오프라인 도난 시 SQLCipher 키 모름 → 데이터 추출 불가.

#### 대응 7: 게이트웨이 펌웨어 무결성 검증

- 부팅 시 OS·Python 코드 해시 검증 (TPM 모듈 활용)
- 펌웨어 변경 시 본사에 알림 + 부팅 거부

---

## 3. 위협 T-2: ESP32-S3 노드 펌웨어 위조 (P1)

### 3.1 위협 시나리오

악의적 행위자가:
- ESP32-S3 노드를 추출해 펌웨어 분석
- 가짜 ESP32-S3 노드를 매장에 추가 설치
- 가짜 CSI 데이터를 매장 게이트웨이에 송신해 알고리즘 교란

결과:
- 본사 분석 결과 오염
- 매장 운영 의사결정 오도
- 경쟁사 음모 시나리오 (낮은 가능성)

### 3.2 대응 5가지

#### 대응 1: 노드-게이트웨이 페어링 (TLS Mutual Auth)

- 각 ESP32-S3 노드에 X.509 인증서 임베드 (제조 시)
- 매장 게이트웨이 ↔ 노드 통신: MQTT over TLS 1.3 + Mutual Auth
- 가짜 노드는 인증서 없으므로 게이트웨이 거부

#### 대응 2: 노드 등록 화이트리스트

```python
# 매장 게이트웨이가 등록된 노드만 수신
ALLOWED_NODES = {
    "node_fitting_3_a": "사이즈 시리얼·MAC·인증서 fingerprint",
    "node_fitting_3_b": "...",
    # 6개 노드만 화이트리스트
}

def accept_node_data(node_id, data):
    if node_id not in ALLOWED_NODES:
        log_security_event(f"Unknown node: {node_id}")
        return False
    return verify_signature(data, ALLOWED_NODES[node_id])
```

#### 대응 3: 노드 데이터 이상 감지

```python
# 통계적 이상 감지
def detect_anomaly(node_data):
    """노드별 데이터 통계 이상 감지."""
    
    # RSSI 분포 학습 (지난 30일)
    historical_rssi_mean = get_historical_mean(node_id)
    historical_rssi_std = get_historical_std(node_id)
    
    # 현재 RSSI가 통계 분포 벗어나면 알람
    if abs(current_rssi - historical_rssi_mean) > 3 * historical_rssi_std:
        log_security_event(f"Anomaly: {node_id}, RSSI deviation")
        return False
    
    return True
```

#### 대응 4: 매장 매니저 시각 점검

- 매장 직원 교육: *"피팅룸에 새로운 장치 보이면 매니저에게 보고"*
- 월 1회 노드 시각 점검 매뉴얼
- 매니저 본인 대시보드에 *"등록 노드 수 6개"* 표시

#### 대응 5: 매장 도입 시 노드 위치 사진 등록

- 도입 시 각 노드 설치 위치를 사진으로 기록
- 변경 시 본사 대시보드에서 확인

---

## 4. 위협 T-3: 본사 대시보드 권한 우회 (P0)

### 4.1 위협 시나리오

- 본사 A의 사용자가 본사 B의 데이터 접근 시도
- SQL Injection으로 Athena 쿼리 우회
- API Gateway 요청 위조 (JWT 위조 등)
- 본사 사용자가 본인 권한 이상 요청

### 4.2 대응 8가지

#### 대응 1: Cognito JWT 검증 강제

```python
def lambda_handler(event, context):
    # API Gateway가 Cognito JWT 자동 검증
    # Lambda는 검증된 claims만 사용
    
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    brand_id = claims["custom:brand_id"]
    role = claims["custom:role"]
    
    # brand_id 절대 사용자 입력에서 받지 않음 (JWT에서만)
    return query_with_isolation(brand_id, role, ...)
```

#### 대응 2: Athena 쿼리의 brand_id 강제 주입

```python
def execute_athena_query(brand_id, user_query_intent):
    """사용자는 쿼리 직접 작성 못 함, intent만 선택."""
    
    # 잘못된 패턴 (SQL Injection 위험)
    # query = f"SELECT * FROM mart WHERE {user_query}"
    
    # 올바른 패턴 (intent → 미리 정의된 쿼리)
    if user_query_intent == "weekly_hesitation":
        query = """
            SELECT * FROM mart.joint_signals 
            WHERE brand_id = %(brand_id)s 
              AND date BETWEEN %(start)s AND %(end)s
              AND signal_type = 'hesitation'
        """
        return athena.execute(query, params={"brand_id": brand_id, ...})
```

#### 대응 3: IAM Role per Brand

각 본사별 별도 IAM Role 생성:

```yaml
arn:aws:iam::123456789012:role/tryops-brand-001-reader
  Trust: Cognito user with custom:brand_id=brand_001
  Permissions:
    - s3:GetObject on s3://tryops-data/*/brand_id=brand_001/*
    - athena:StartQueryExecution on workgroup brand_001
    - athena:GetQueryResults on workgroup brand_001
  Deny:
    - s3:GetObject on s3://tryops-data/*/brand_id=NOT brand_001/*
```

#### 대응 4: S3 Prefix 권한 정밀화

```yaml
s3://tryops-data/
├── raw/brand_id=brand_001/  → brand_001 IAM Role만 접근
├── raw/brand_id=brand_002/  → brand_002 IAM Role만 접근
├── mart/brand_id=brand_001/ → brand_001 IAM Role만 접근
└── ...
```

#### 대응 5: API Rate Limiting

```yaml
API Gateway Rate Limit:
  - 본사 사용자당: 100 요청/분
  - 본사 전체: 1,000 요청/분
  - 글로벌: 10,000 요청/분
  
초과 시: HTTP 429 Too Many Requests
```

#### 대응 6: 매장 게이트웨이 API Rate Limit

```yaml
매장 게이트웨이 → API Gateway:
  - 매장당: 60 요청/분 (5분 배치라 충분)
  - 초과 시 차단 (악의적 데이터 폭증 방어)
```

#### 대응 7: 권한 변경 감사 로그

```python
# 모든 권한 변경 (role 변경·store_ids 변경 등) 로깅
def change_user_role(user_id, new_role, admin_user_id):
    log_audit({
        "action": "role_change",
        "target_user": user_id,
        "old_role": get_user_role(user_id),
        "new_role": new_role,
        "performed_by": admin_user_id,
        "timestamp": now()
    })
    apply_role_change(user_id, new_role)
```

#### 대응 8: 정기 권한 감사

- 분기별 권한 검토 (본사 SRE + TryOps 보안 담당)
- 부재 사용자 (90일 미접속) 자동 비활성화
- 본사 퇴사자 권한 즉시 폐기 매뉴얼

---

## 5. 위협 T-4: AWS S3 데이터 격리 (P1)

### 5.1 위협 시나리오

- 잘못된 IAM 정책으로 본사간 데이터 접근
- 개발자 실수로 S3 bucket public 노출
- 백업 데이터의 격리 누락

### 5.2 대응 6가지

#### 대응 1: S3 Bucket Public Access Block

```yaml
S3 Bucket 설정 (강제):
  BlockPublicAcls: true
  IgnorePublicAcls: true
  BlockPublicPolicy: true
  RestrictPublicBuckets: true
  Versioning: enabled
  ServerSideEncryption: SSE-KMS (브랜드별 키)
```

#### 대응 2: KMS Customer Master Key per Brand

```yaml
브랜드당 KMS 키:
  brand-001-data-key:
    Description: TryOps brand_001 data encryption
    KeyUsage: ENCRYPT_DECRYPT
    KeyPolicy: brand_001 IAM Role만 사용 가능
  brand-002-data-key:
    ...
```

- 본사간 키 격리
- 본사가 *"우리 키 폐기"* 요청 시 즉시 데이터 접근 불가
- GDPR Article 17 (Right to be Forgotten) 대응

#### 대응 3: VPC Endpoint for S3

- S3 트래픽이 인터넷 안 거치고 VPC 내부에서만
- 외부 노출 차단

#### 대응 4: S3 Object Lock (선택)

- 본사 계약 종료 후 90일 데이터 보존 기간 강제
- Compliance Mode로 삭제 차단
- 법적 분쟁 시 데이터 무결성 보장

#### 대응 5: 백업 데이터의 격리 유지

- S3 Replication 시 동일 IAM 정책·KMS 키 적용
- Cross-Region Replication 시 대상 리전에도 같은 격리

#### 대응 6: 보안 스캔 자동화

- AWS Security Hub 활성화
- AWS GuardDuty (이상 행동 탐지)
- AWS Macie (S3 개인정보 자동 탐지)

🟢 모두 AWS 공식 서비스, 매장 100개 기준 월 약 $20~50 추가.

---

## 6. 멀티테넌트 격리 통합 매트릭스

본사간 격리를 보장하는 레이어 5가지:

| 레이어 | 격리 방법 | 검증 |
|---|---|---|
| Cognito | Custom Attribute `custom:brand_id` | JWT claims 강제 |
| IAM | 본사별 IAM Role | Role assumption 검증 |
| Lambda | JWT claims → brand_id 추출 → 쿼리 강제 주입 | 단위 테스트 |
| Athena | 본사별 Workgroup | 쿼리 권한 검증 |
| S3 | 본사별 prefix + KMS 키 | bucket policy 검증 |

**Defense in Depth**: 한 레이어 실패해도 다음 레이어가 차단.

---

## 7. 보안 모니터링 & 감사

### 7.1 실시간 알람

```yaml
CloudWatch Alarms:
  - API Gateway 4xx > 100/분 → 잠재 공격 의심
  - Cognito sign-in 실패 > 10/분 per IP → 무차별 대입 의심
  - S3 GetObject deny > 50/분 → 권한 침해 시도
  - Lambda 에러율 > 5% → 시스템 문제 또는 공격
  - 매장 게이트웨이 heartbeat 없음 > 30분 → 도난·장애
```

### 7.2 보안 감사 로그 (CloudTrail)

```yaml
CloudTrail 활성화:
  - Multi-Region: true
  - Read·Write 모두 기록
  - S3 적재 (별도 격리 bucket)
  - 90일 보존 (법적 요구 시 1년+)
```

### 7.3 정기 감사

| 주기 | 작업 |
|---|---|
| 일 | CloudWatch 알람 점검 |
| 주 | GuardDuty 발견 사항 검토 |
| 월 | 권한 변경 로그 점검 |
| 분기 | 본사·사용자 권한 전체 감사 |
| 연 | 외부 보안 감사 (KISA · 한국정보보호산업협회) |

---

## 8. 한국 법규 준수 매핑

### 8.1 개인정보보호법 (legal_review.md 섹션 1·2·3)

- 🟢 영상정보처리기기 제25조: WiFi CSI는 영상 아님, 면제
- 🟢 정보주체 권리 (열람·삭제·처리정지): 본사 대시보드에 *"내 데이터 삭제"* 기능 (요청 시)
- 🟢 가명/익명 격리: raw 데이터는 매장 게이트웨이만, AWS는 익명 집계

### 8.2 정보통신망법

- 🟢 개인정보 암호화 의무: SQLCipher (매장) + KMS (AWS)
- 🟢 접속 기록 보존 1년: CloudTrail
- 🟢 권한 관리 매뉴얼: 본 문서

### 8.3 GDPR (글로벌 확장 시)

- 🟡 Right to Access: 본사 사용자가 본인 데이터 요청 가능
- 🟡 Right to Erasure: KMS 키 폐기로 본사 데이터 즉시 무효화
- 🟡 Data Processing Agreement: 본사와 별도 계약

### 8.4 KISA 보안성 평가

진짜 사업 시 KISA 보안성 평가 통과 필수:
- 보안 통제 70개 항목
- 외부 침투 테스트
- 본 문서 + 정기 감사 로그가 평가 자료

---

## 9. 보안 인시던트 대응 매뉴얼

### 9.1 인시던트 유형별 대응

| 인시던트 | 즉시 대응 | 24시간 내 | 1주 내 |
|---|---|---|---|
| 매장 게이트웨이 도난 | API 키 폐기 + Remote Wipe 시도 | 본사 통보 + 새 게이트웨이 발송 | 보안 감사 |
| 데이터 유출 의심 | CloudTrail 로그 분석 + GuardDuty 점검 | 본사 통보 (개인정보보호법 의무) | 한국인터넷진흥원 신고 |
| DDoS 공격 | AWS Shield Standard (자동) + Rate Limit 강화 | WAF 규칙 추가 | 인프라 보강 |
| 본사 사용자 계정 탈취 | 비밀번호 강제 재설정 + MFA 활성화 | 권한 검토 + 활동 로그 분석 | 본사 보안 교육 |
| AWS 측 보안 사고 | AWS Support 즉시 콜 + 트래픽 격리 | 본사 통보 + 영향 평가 | 재발 방지 |

### 9.2 인시던트 보고 채널

```
[L1 인지] 매장 매니저 / 본사 사용자 / CloudWatch 알람
   ↓
[L2 분석] TryOps SRE / 보안 담당
   ↓
[L3 대응] 본사 사용자 통보 + AWS Support
   ↓
[L4 법무] 한국인터넷진흥원 + 본사 법무팀 (개인정보 유출 시 24시간 내 의무)
```

---

## 10. 보안 비용 추정

본 설계 추가 비용:

### 10.1 AWS 운영 보안 비용 (매장 100개 기준)

| 항목 | 월 비용 (USD) | 비고 |
|---|---|---|
| GuardDuty | $15 | 본 시점 |
| Security Hub | $5 | 본 시점 |
| Macie (선택) | $10 | 데이터 5GB 기준 |
| WAF | $5 | 기본 규칙 |
| AWS Shield Advanced | $3,000 | 매장 500+ 시 검토 |
| KMS Keys (브랜드별 5개) | $5 | $1/키/월 |
| **합계 (Phase 1·2)** | **$40** | 매장 100개 시 매장당 $0.4 추가 |

### 10.2 인증·감사 1회성 비용 (v2 셀프리뷰 본질 5 정정)

본 v2가 KISA 외부 침투 테스트 *"1,000~3,000만원"* 만 명시. **실제 한국 보안 인증 비용은 훨씬 큼**.

| 인증·감사 | 비용 (만원) | 주기 | 도달 시점 |
|---|---|---|---|
| KISA 외부 침투 테스트 | 1,000~3,000 | 연 1회 | PoC 1매장 도입 시 |
| ISMS-P (개인정보보호 인증) | **5,000~10,000** | 3년 1회 + 매년 사후심사 | 매장 30~50개 도달 시 |
| ISO 27001 | 3,000~7,000 | 3년 1회 + 매년 갱신 | 매장 100개 + 글로벌 진출 시 |
| SOC 2 Type II (글로벌 본사 영업 시) | 5,000~15,000 | 연 1회 | 글로벌 매장 진출 |
| 한국 법무법인 정식 의견서 | 500~1,500 | 1회 (정기 업데이트) | PoC 시작 시 |

**누적 보안 인증 비용**:
- PoC 1년차: 약 **1,500~4,500만원** (KISA 1회 + 법무 의견서)
- Phase 2 (매장 50개): 약 **5,000~1억원 누적** (ISMS-P 추가)
- Phase 3 (매장 100개+): 약 **1억~2.5억원 누적** (ISO 27001 + 글로벌 진출 시 SOC 2)

🔴 본 v2가 *"보안 = 1,000만원 정도면 됨"* 의 톤이었으나 실제는 **5~10배 비용**. 자금 계획·CFO 결재 시 반드시 반영.

### 10.3 보안 인력 비용

- Phase 3 도달 시 시니어 보안 엔지니어 1.0 FTE 필수 (`devops_setup.md` 섹션 8.3)
- 월 약 1,000~1,300만원 → 연 약 1.2억~1.6억원
- 외주 보안 컨설팅: 사건 발생 시 시간당 30~50만원

### 10.4 보안 ROI

보안 투자의 회피 가능 손실:
- 개인정보 유출 사고 1건당 평균 손실: 약 **15억~50억원** (KISA 2024 보고서 기반)
- 본사 1곳 이탈 영향: 매장당 ARR × 매장 수
- 평판·SNS 위기: 정량화 어려우나 K-D2C 본사 전체 신뢰도 영향

본 보안 투자 누적 약 1억~2.5억원 → **회피 손실 15억+** 으로 **ROI 6~15배**.

---

## 11. 본 보안 설계 v1의 한계

본 v1은:
- 🔴 실제 보안 감사 미진행
- 🔴 침투 테스트 결과 없음
- 🔴 KISA 보안성 평가 미통과
- 🔴 ESP32-S3 펌웨어 보안 검증 미진행 (HW 보안 모듈 활용도)
- 🔴 매장 게이트웨이 SQLCipher 성능 영향 미측정

**진짜 사업 시작 시**: PoC 매장 1개 도입 시점에 보안 감사 1회 + 매장 30개 도달 시점에 KISA 평가.

**본 문서 활용 가이드**: 본사 보안 담당자 검토 시 위협 4가지 + 대응 매트릭스 + 격리 5레이어 제출. 보안 감사 시 본 문서 + CloudTrail 로그 + 권한 변경 로그가 기본 자료.
