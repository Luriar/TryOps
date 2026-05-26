# Tech Stack Evolution — Phase 1·2 → Phase 3+ 진화 경로

> 본 문서는 `architecture.md` 섹션 5 Phase 3 진화 트리거의 상세 자료다. 매장·본사 수 증가에 따른 시스템 진화 단계 + 마이그레이션 가이드.

---

## 0. 본 문서의 핵심 명제

**진화는 *"미리 하지 않음"***. Phase 1·2 설계가 매장 200개까지 안정 동작하므로 그 이상 도달 시점에만 진화한다.

본 문서는 *"언제 어떻게 진화할지"* 의 트리거 + 마이그레이션 매뉴얼.

---

## 1. Phase별 시스템 구조

### 1.1 Phase 1: PoC 단계 (매장 1~3개)

```
[매장]
ESP32-S3 → Raspberry Pi 4B (집계) → AWS Firehose → S3 Parquet
                                        ↓
                              EC2 t4g.small (Polars + DuckDB + Airflow)
                                        ↓
                                    Athena + Lambda
                                        ↓
                              Cloudflare Pages (Next.js)
```

특징:
- 단순함이 핵심
- EC2 t4g.small 1대로 모든 ETL
- 매장 게이트웨이 SW도 미숙 → 매번 SSH로 직접 패치

### 1.2 Phase 2: 초기 확장 (매장 10~100개)

Phase 1과 동일 구조 + 다음 개선:
- 매장 게이트웨이 OTA 업데이트 시스템 도입
- CloudWatch Logs 분석 본격화
- 멀티 테넌트 격리 검증
- 백업·재해 복구 자동화

### 1.3 Phase 3: 본격 확장 (매장 100~500개)

진화 트리거 도달 시 다음 변경:

| 컴포넌트 | Phase 1·2 | Phase 3 | 이유 |
|---|---|---|---|
| ETL 엔진 | EC2 t4g.small | **EC2 m6g.large** 또는 EMR Serverless | 데이터량 증가 |
| Athena | On-demand | (검토) **Provisioned Capacity** | 일 1.92TB+ scan 시 손익분기 |
| 메타데이터 DB | DynamoDB | **RDS Postgres** (multi-AZ) | 관계형 쿼리 증가 |
| 실시간 처리 | Firehose 60초 | **Kinesis Data Streams + Lambda** | <60초 알람 요구 |
| Cognito | User Pools | + **Identity Pools** | 매장 게이트웨이 IoT 인증 |

### 1.4 Phase 4: 대규모 (매장 500~5,000개)

| 컴포넌트 | Phase 3 | Phase 4 | 이유 |
|---|---|---|---|
| ETL 엔진 | EC2 m6g.large | **EMR Serverless + PySpark** | 다중 매장 동시 처리 |
| 메타데이터 DB | RDS Postgres | **Aurora Serverless v2** | 자동 스케일 |
| 분석 마트 | S3 Parquet | + **Redshift Serverless** | 본사 대시보드 응답 <2초 |
| 캐싱 | Lambda 메모리 | + **ElastiCache Redis** | 본사 대시보드 캐싱 |
| 실시간 알람 | Lambda | + **Flink on KDA** | 복잡 윈도우 처리 |

### 1.5 Phase 5: 글로벌 (매장 5,000+)

| 컴포넌트 | Phase 4 | Phase 5 | 이유 |
|---|---|---|---|
| 리전 | ap-northeast-2 | + **us-east-1 / ap-southeast-1** | K-패션 글로벌 확장 |
| 데이터 라우팅 | 단일 리전 | **글로벌 라우팅** (Route 53) | 매장 → 가장 가까운 리전 |
| 본사 대시보드 | Cloudflare Pages | + **CloudFront 멀티 리전** | 글로벌 본사 응답 빠름 |
| 데이터 동기화 | - | **S3 Cross-Region Replication** | 본사 통합 분석 |
| 통화 | KRW | + **다중 통화** | 글로벌 본사 가격 정책 |

---

## 2. Phase 3 진화 트리거 5가지

### 2.1 트리거 A: EC2 t4g.small CPU 80%+ (매장 300개+ 추정)

**감지**:
- CloudWatch CPU 메트릭 5분 평균 >80% 지속 1주
- ETL 처리 시간 > DAG 실행 간격 (1시간 DAG가 1시간 넘게 걸림)

**즉시 대응 (1단계)**:
- EC2 인스턴스 타입 t4g.small → **t4g.medium → t4g.large → m6g.large** 단계별 스케일업
- 다운타임: 약 5~10분 (인스턴스 재시작)

**근본 대응 (2단계)**:
- EMR Serverless로 마이그레이션
- 마이그레이션 작업: 약 1~2주
- 비용: EMR Serverless 약 $0.052/vCPU-hour (사용량 비례)

### 2.2 트리거 B: 일 Athena scan 50TB+ (본사 30~50개 추정)

**감지**:
- Athena 월 비용 $250+ (50TB × $5)
- 일평균 1.92TB scan 도달 시 Provisioned Capacity 손익분기

**즉시 대응**:
- Athena Provisioned Capacity 24 DPU 활성화 (월 $6,912 vs 50TB × $5 × 30일 = $7,500)
- 손익분기 약 50TB/일

**근본 대응**:
- Redshift Serverless 검토 (반복 쿼리는 Redshift가 빠름)
- 본사 대시보드의 *"실시간 쿼리 vs 캐시 쿼리"* 분리

### 2.3 트리거 C: 실시간 알람 < 60초 요구 (Assistance Need 본격)

**감지**:
- 본사·매장 매니저 피드백: *"피팅룸 도움 알람이 너무 늦다"*
- Firehose 60초 버퍼링 본 한계

**즉시 대응**:
- Assistance Need만 Kinesis Data Streams로 분리
- 매장 게이트웨이 → Lambda 직접 (Firehose 우회)
- 추가 비용: Data Stream on-demand $0.04/GB + stream $29/월

**근본 대응**:
- Flink on Kinesis Data Analytics (KDA) 도입
- 복잡 윈도우 (5분 / 10분 / 시간) 동시 처리
- Phase 4 단계

### 2.4 트리거 D: 본사 1,000개+ (Cognito 무료 한도 초과)

**감지**:
- Cognito MAU >50,000
- 사용자당 $0.0055 추가 비용 발생

**대응**:
- Cognito Identity Pools로 매장 IoT 인증 분리
- B2B 본사 사용자는 Cognito User Pools 유지
- 또는 Auth0·Okta 같은 외부 IdP 통합 검토

### 2.5 트리거 E: 데이터 보존 정책 변경 (1년+ 보존 요구)

**감지**:
- 본사가 *"3년치 트렌드 분석"* 요구
- S3 Standard 1년+ 데이터 비용 부담

**대응**:
- **S3 Intelligent-Tiering** 활성화 (90일+ 자동 IA, 180일+ Glacier)
- 비용 절감 약 40~60%
- 단, 옛 데이터 조회 시 30초~분 단위 지연

---

## 3. 마이그레이션 가이드 — Phase 2 → Phase 3

가장 큰 진화 단계인 Phase 2 → 3 마이그레이션 매뉴얼.

### 3.1 사전 점검 체크리스트

- [ ] 매장 수 200개 도달
- [ ] CloudWatch CPU 7일 평균 70%+
- [ ] 본사 5~10개 도달
- [ ] 월 청구 $50+ 도달
- [ ] 데이터팀 1명 추가 채용 완료

위 5개 모두 충족 시 Phase 3 마이그레이션 착수.

### 3.2 마이그레이션 단계 (총 약 4주)

**Week 1: EC2 스케일업**
- t4g.small → m6g.large 전환 (단순)
- CloudWatch 메트릭 1주 모니터링
- 성공 시 Week 2 진입, 실패 시 Phase 2 유지

**Week 2: EMR Serverless 평가**
- 기존 Polars + DuckDB 코드 → PySpark 마이그레이션 일부 (대표 DAG 3개)
- 처리 시간·비용 비교
- 결과로 마이그레이션 여부 결정

**Week 3: 메타데이터 RDS 마이그레이션**
- DynamoDB → RDS Postgres
- 데이터 마이그레이션 스크립트
- API Lambda 업데이트
- 다운타임 1시간 (계획적)

**Week 4: 멀티 테넌트 강화**
- Cognito 권한 모델 정밀화
- 본사별 IAM 정책 검증
- 보안 감사

### 3.3 롤백 계획

각 단계마다 롤백 가능:
- EC2: 인스턴스 타입 즉시 변경 (10분)
- EMR vs Polars: 두 시스템 병행 운영 1주
- RDS vs DynamoDB: 듀얼 라이트 1주 후 전환

### 3.4 비용 영향

| 항목 | Phase 2 (매장 200) | Phase 3 (매장 300) | 차이 |
|---|---|---|---|
| EC2 | $15 (t4g.small) | $50 (m6g.large) | +$35 |
| EMR Serverless (선택) | - | $50~100 | +$75 |
| RDS Postgres | - | $13 (db.t4g.micro) | +$13 |
| Cognito | $0 | $0 | $0 |
| **합계** | **~$50** | **~$130** | **+$80** |

매장 200개 → 300개 (+50%) 시 비용 +60% 증가. 정상 범위.

---

## 4. Phase별 코드 호환성 보장

### 4.1 Polars → PySpark 호환 작성

Phase 1·2에서 Polars 코드를 PySpark 호환 패턴으로 작성:

```python
# 호환 패턴 (Polars 및 PySpark 둘 다 동작)
def calculate_hesitation(df):
    return (
        df.group_by(["store_id", "fitting_room_id", "session_id"])
        .agg([
            pl.col("size_swap_count").sum(),
            pl.col("activity_score").mean(),
            pl.col("session_duration").max()
        ])
        .with_columns([
            (pl.col("size_swap_count") * 0.4 + 
             pl.col("activity_score") * 0.3 + 
             pl.col("session_duration").alias("hesitation_score"))
        ])
    )
```

**호환성 원칙**:
- `groupby()` 대신 `group_by()` (Polars 명확)
- `.agg([pl.col(...)])` 패턴 (Spark도 유사)
- `.with_columns()` (Spark의 `.withColumn()`과 호환)
- 복잡 UDF 회피, expression 우선

마이그레이션 시 90% 코드 그대로, 10% 만 수정.

### 4.2 DuckDB → Redshift 호환

DuckDB SQL을 Redshift 호환으로 작성:
- ANSI SQL 표준 사용
- DuckDB 전용 함수 (`list_aggregate` 등) 회피
- Window 함수 우선 활용

### 4.3 DynamoDB → RDS 마이그레이션

데이터 모델링 사전 정비:
- DynamoDB도 *"관계형으로 정규화 가능한"* 형태로 저장
- Single-table design 회피
- PK + SK 명확히 분리

---

## 5. 진화 의사결정 매트릭스

각 진화 시점의 *"진화 vs 유지"* 의사결정 가이드.

### 5.1 진화 우선순위

| 우선순위 | 진화 대상 | 트리거 |
|---|---|---|
| P0 (긴급) | EC2 스케일업 | CPU 90%+ 1일 |
| P1 (높음) | RDS Postgres 전환 | 메타데이터 5GB+ |
| P2 (중간) | EMR Serverless | EC2 m6g.large도 부족 |
| P3 (낮음) | Redshift Serverless | 본사 대시보드 응답 5초+ |
| P4 (선택) | Multi-region | 글로벌 매장 도달 |

### 5.2 *"진화하지 않을 것"* 리스트

다음은 매장 1,000개까지도 진화 안 함:

- ❌ Kubernetes 도입 (Lambda + EC2 충분)
- ❌ 마이크로서비스 분리 (단일 백엔드 충분)
- ❌ 자체 메시지 큐 (Kinesis 충분)
- ❌ ElasticSearch (Athena 충분)
- ❌ 다국어 지원 (한국 중심)

이게 *"가장 싸게"* 의 핵심 — 불필요한 진화 차단.

---

## 6. 진화 비용 시뮬레이션

매장 수별 누적 진화 비용:

| 단계 | 매장 수 | 누적 진화 작업 | 추가 인력 | 월 운영비 |
|---|---|---|---|---|
| Phase 1 | 1~3 | - | 0명 (사용자 1인) | $16 |
| Phase 2 | 10~100 | 매장 게이트웨이 OTA, 백업 자동화 | 0명 (사용자 1인) | $51 |
| Phase 2-Late | 100~200 | 모니터링 강화 | 1명 (DevOps 또는 SRE) | $80 |
| Phase 3 | 200~500 | EC2 스케일업, RDS 전환 | 2명 (DevOps + 데이터 엔지니어) | $200 |
| Phase 3-Late | 500~1000 | EMR Serverless, Redshift | 3명 | $500 |
| Phase 4 | 1000~5000 | Multi-AZ, ElastiCache | 5명 | $1,500 |
| Phase 5 | 5000+ | Multi-region | 8명+ | $5,000+ |

## 6.5 매장 게이트웨이 SW + 펌웨어 개발 일정 (비판 4 해소)

본 v1이 *"Raspberry Pi + Python + Polars + SQLite"* 만 명시. 실제 개발 공수의 일정·인력 표.

### 6.5.1 매장 게이트웨이 SW (Python)

| 작업 | 소요 기간 | 인력 | 출력물 |
|---|---|---|---|
| 기본 골격 (collector·집계·SQLite) | 4주 | Backend 1명 | 매장 1개 데이터 수집 가능 |
| RFID webhook 통합 (셀메이트·idro 등 5개 솔루션사) | 3주 | Backend 1명 | 5개 솔루션사 지원 |
| POS API 통합 (토스플레이스·NHN KCP·NICE) | 3주 | Backend 1명 | 3개 POS 지원 |
| OTA 업데이트 시스템 | 3주 | DevOps + Backend | 매장 원격 배포 가능 |
| 매장 매니저 로컬 UI (Phase 2+) | 4주 | Frontend 1명 | 매니저 본인 대시보드 |
| 보안 강화 (SQLCipher, API 키 회전) | 2주 | Backend + 보안 | security_design.md 충족 |
| 테스트 자동화 (LocalStack 통합) | 2주 | QA 1명 | E2E 자동화 |
| **합계** | **약 21주 (5개월)** | **약 1.5 FTE** | **PoC 매장 가동 가능** |

### 6.5.2 ESP32-S3 펌웨어 (C++/ESP-IDF)

| 작업 | 소요 기간 | 인력 | 출력물 |
|---|---|---|---|
| ESP32-S3 보드 셋업 + ESP-IDF 빌드 | 1주 | 펌웨어 1명 | 보드 부팅 |
| ESP-CSI 라이브러리 통합 | 2주 | 펌웨어 1명 | CSI 추출 가능 |
| MQTT publish (매장 게이트웨이 송신) | 2주 | 펌웨어 1명 | 1초 단위 데이터 송신 |
| X.509 인증서 + Mutual TLS (보안) | 2주 | 펌웨어 + 보안 | security_design.md 충족 |
| OTA 펌웨어 업데이트 | 2주 | 펌웨어 + DevOps | 원격 펌웨어 배포 |
| 매장 환경 캘리브레이션 | 2주 | 펌웨어 + 데이터 | 노이즈 보정 알고리즘 |
| 테스트 자동화 | 1주 | 펌웨어 1명 | 단위 + HIL 테스트 |
| **합계** | **약 12주 (3개월)** | **약 0.5 FTE** | **6개 노드 안정 동작** |

🔴 **펌웨어 개발은 외주 권장** (1인 6개월 비용 약 5,000~8,000만원).

### 6.5.3 전체 PoC 1매장 가동 일정

```
Week 1~4:    매장 게이트웨이 기본 골격 + ESP32 셋업 (병행)
Week 5~8:    RFID + POS + ESP-CSI 통합
Week 9~12:   OTA + 보안 강화
Week 13~16:  테스트 자동화 + 매장 1개 설치 시도
Week 17~20:  매장 환경 캘리브레이션 + 안정화
Week 21~24:  매장 매니저 로컬 UI

총 6개월 후 PoC 매장 1개 안정 가동 가능
```

### 6.5.4 매장 솔루션사별 통합 추가 일정

매장 추가 시 RFID·POS 솔루션사별 통합 작업:

| 신규 솔루션사 | 통합 시간 | 작업 |
|---|---|---|
| RFID 솔루션사 신규 | 1~2주 | webhook 스키마 분석 + Adapter 코드 |
| POS 솔루션사 신규 | 1~2주 | API 스키마 분석 + 인증 통합 |
| 본사별 맞춤 통합 | 0.5~1주 | 본사 ERP·SCM 인터페이스 |

🔴 매장 100개 도달 시 매장당 평균 1~2개 솔루션사 통합 필요. 누적 통합 작업 약 100~200주.

→ **Phase 2 (매장 10~30개) 시 *"표준 통합 가이드"* 작성으로 단축 필수**. 새 솔루션사 통합 1~2주 → 2~3일로 단축 목표.

---

## 7. 시점 의사결정 가이드

### 7.1 *"지금 진화해야 하는가?"* 자가 점검

```
체크리스트:
- [ ] CloudWatch 알람이 일주일 내 3회+ 울렸는가?
- [ ] 본사·매장 매니저로부터 성능 불만 받았는가?
- [ ] ETL DAG가 일별 1회+ 실패하는가?
- [ ] 월 청구가 예상 50%+ 초과했는가?
- [ ] 데이터팀이 *"리소스 부족"* 보고했는가?

3개 이상 ✅ → 진화 검토 진입
1~2개 ✅ → 모니터링 강화 + Phase 유지
0개 ✅ → 진화 절대 금지 (premature optimization)
```

### 7.2 *"진화 후 1개월 검증"*

진화 작업 후 다음 메트릭 확인:

| 메트릭 | 기대값 | 실측 |
|---|---|---|
| 매장당 한계비용 | 예상 ±20% 이내 | (실측) |
| ETL 처리 시간 | 50% 단축 | (실측) |
| 본사 대시보드 응답 | 30% 빠름 | (실측) |
| 장애 발생률 | 절반 | (실측) |

기대값 미달 시 진화 결정 재검토.

---

## 8. 본 진화 가이드의 한계

본 v1 가이드는:

- 🔴 실제 진화 경험 0건 (시뮬레이션만)
- 🔴 매장당 데이터량 가정의 변동성 미반영
- 🔴 Phase 4~5는 추정만, 실제 도달 가능성 미검증
- 🔴 글로벌 확장 시 통화·법규 차이 미반영

**진짜 사업 시작 시**: Phase 1·2 실제 운영 데이터로 v2 가이드 갱신. Phase 3 진입 시점에 v3.

**본 문서 활용 가이드**: Phase 1·2 운영 중 *"진화 압박"* 받을 때 트리거 5가지 점검. *"진화하지 않을 것"* 리스트로 불필요한 복잡도 차단.
