# DEVLOG.md — 서울시 개별공시지가 정보 MCP

기록 형식:
```
## YYYY-MM-DD
- 진행 내용:
- 확인 필요 / 실측 결과:
- 문제 및 해결:
```

---

## 2026-08-16
- 진행 내용: DEVPLAN.md/CLAUDE.md/README.md/DEVLOG.md 4종 문서 생성 완료 (Claude 웹챗 단계)
- 확인 필요 / 실측 결과:
  - START_INDEX/END_INDEX로 실제 여러 건이 반환되는지 미확인 (명세서상으로는 최대 1000건 차이까지 가능하다고 되어 있으나 실제 API 동작은 로컬 테스트 단계에서 실측 필요)
  - BASE_MON(기준년월) 필드 포맷(YYYYMM 추정) 실측 필요
- 문제 및 해결: 해당 없음 (아직 구현 전)

## 2026-08-16 (구현 단계)
- 진행 내용:
  - requirements.txt, seoul_api.py, server.py 작성 완료 (`mcp.run(..., stateless_http=True)` 반영)
  - .venv 생성 후 fastmcp/httpx/python-dotenv 설치
  - FastMCP 서버 임포트 및 `list_tools()` 스모크 테스트 통과 — 툴 1개(`get_individual_land_price`)만 등록됨 확인
  - Dockerfile, fly.toml 작성 완료
- 확인 필요 / 실측 결과 (⚠️ 미해결):
  - 실제 `.env`의 `SEOUL_API_KEY`(30자리 hex 형태)로 `IndividuallyPostedLandPriceService` 호출 시
    **일관되게 `ERROR-500` (서버 오류) 반환** — 동일 요청을 3회 재시도했으나 동일하게 실패 (CLAUDE.md 3회 재시도 규칙에 따라 중단).
  - URL 경로 구조는 DEVPLAN.md 스펙대로 11개 세그먼트(KEY/json/IndividuallyPostedLandPriceService/START/END/SIGUNGU_NM////  /2020)를 구성했고,
    `sample` 키로도 동일 패턴 테스트 시 `ERROR-300`(필수값 누락)이 발생해 URL 구조 자체에 대한 확신이 낮음.
  - 서비스명 대소문자를 바꿔보면(`individuallyPostedLandPriceService`) 에러 코드가 `ERROR-300`→`ERROR-500`으로 달라지는 것을 확인 — 이는 API가 요청을 다르게 처리하고 있다는 신호이나 근본 원인은 특정하지 못함.
  - **가능성 있는 원인 (실측 불가, 사용자 확인 필요)**:
    1. `.env`의 키가 이 특정 서비스(IndividuallyPostedLandPriceService)에 대해 활성화되지 않았을 가능성 (서울 열린데이터광장은 서비스별로 키를 재승인해야 하는 경우가 있음)
    2. 키 형식이 일반적인 서울 열린데이터광장 키(24자 영숫자)와 달리 30자리 hex 형태로 보여, 다른 시스템의 키가 잘못 저장되었을 가능성
    3. START_INDEX/END_INDEX 실측(여러 건 반환 여부), BASE_MON 포맷 실측은 이 오류로 인해 **아직 수행하지 못함**
  - **코드 자체는 DEVPLAN.md 스펙대로 구현 완료**되어 있으며, 유효한 키로 재시도하면 바로 검증 가능한 상태.
- 문제 및 해결:
  - 문제: 실제 API 호출이 ERROR-500으로 지속 실패해 END-TO-END 실측을 완료하지 못함.
  - 해결(보류): 사용자가 서울 열린데이터광장에서 `IndividuallyPostedLandPriceService`용 키가 정상 승인되었는지 확인 후 재테스트 필요. 코드 수정 없이 유효한 키만 있으면 바로 검증 가능.
