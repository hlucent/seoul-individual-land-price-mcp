# DEVPLAN.md — 서울시 개별공시지가 정보 MCP

## 1. API 스펙 요약

- 공공정보명: 서울시 개별공시지가 정보 (IndividuallyPostedLandPriceService)
- 제공기관: 서울특별시 (도시공간본부 토지관리과)
- 원본형태: File (OpenAPI는 2007년 이후 데이터만 제공)
- 적재주기: 매년 5/3, 7/3, 9/3, 1/3 (휴일이면 그 전일)
- 이용허락조건: 공공누리 1유형 (출처표시, 상업적 이용 및 변경 가능)

### 요청 URL 패턴

```
http://openapi.seoul.go.kr:8088/{KEY}/{TYPE}/IndividuallyPostedLandPriceService/{START_INDEX}/{END_INDEX}/{SIGUNGU_NM}/{BJDONG_NM}/{BONBEON}/{BUBEON}/{PILGI_CD}/{YEAR}
```

- `{KEY}`: 인증키 (환경변수 `SEOUL_API_KEY`)
- `{TYPE}`: 응답 형식. `json` 사용 (xml/xmlf/xls도 가능하나 MCP에서는 json 고정)
- 경로 파라미터는 반드시 위 순서 그대로 이어붙인다. **선택 파라미터를 생략할 때도 빈 문자열로 자리만 비우지 말고 통째로 생략하면 안 됨** — 뒤 파라미터 순서가 밀리므로, 값이 없는 선택 파라미터는 빈 문자열(`""`)로 채워 자리를 유지해야 함 (샘플 URL의 공백 슬래시가 이를 보여줌).

### 요청 파라미터

| 변수 | 타입 | 필수여부 | 설명 |
|---|---|---|---|
| KEY | STRING | 필수 | 인증키 |
| TYPE | STRING | 필수 | 응답 파일 타입 (json 고정 사용) |
| SERVICE | STRING | 필수 | `IndividuallyPostedLandPriceService` (URL 경로에 고정 포함, 별도 인자 아님) |
| START_INDEX | INTEGER | 필수 | 요청 시작 위치 (1부터) |
| END_INDEX | INTEGER | 필수 | 요청 종료 위치 (START_INDEX~END_INDEX 최대 1000건 차이) |
| SIGUNGU_NM | STRING | 필수 | 시군구명 (예: 종로구) |
| BJDONG_NM | STRING | 선택 | 법정동명 |
| BONBEON | INTEGER | 선택 | 본번 (0~9999) |
| BUBEON | INTEGER | 선택 | 부번 (0~9999) |
| PILGI_CD | STRING | 선택 | 필지구분코드 (1:토지, 2:임야, 3:가지번, 4:가지번(부분세분), 5:블럭지번, 6:블럭지번(롯트세분), 7:블럭지번(지구), 8:블럭지번(지구-롯트), 9:기타지번) |
| YEAR | STRING | 필수 | 기준년도 (YYYY) |

### 응답 필드 (단위 명시 필수)

| 순번 | 필드명 | 설명 | 단위/비고 |
|---|---|---|---|
| 1 | SIGUNGU_NM | 시군구명 | - |
| 2 | SIGUNGU_CD | 시군구코드 | - |
| 3 | BJDONG_NM | 법정동명 | - |
| 4 | BJDONG_CD | 법정동코드 | - |
| 5 | BONBEON | 본번 | - |
| 6 | BUBEON | 부번 | - |
| 7 | PILGI_NM | 필지구분명 | - |
| 8 | PILGI_CD | 필지구분코드 | - |
| 9 | BASE_MON | 기준년월 | YYYYMM 추정, 실측 필요 |
| 10 | JIGA | 공시지가 | **원/㎡** |
| 11 | YEAR | 기준년도 | YYYY |

### 에러 코드 체계

| 코드 | 의미 |
|---|---|
| INFO-000 | 정상 처리 |
| INFO-100 | 인증키가 유효하지 않음 |
| INFO-200 | 해당하는 데이터가 없음 |
| ERROR-300 | 필수 값 누락 |
| ERROR-301 | TYPE 값 누락/유효하지 않음 |
| ERROR-310 | 해당 서비스를 찾을 수 없음 (SERVICE 확인) |
| ERROR-331 | START_INDEX 값 오류 |
| ERROR-332 | END_INDEX 값 오류 |
| ERROR-333 | 요청위치 값 타입 오류 (정수 아님) |
| ERROR-334 | START_INDEX가 END_INDEX보다 큼 |
| ERROR-335 | 샘플데이터는 한 번에 최대 5건 (샘플키 sample 사용 시) |
| ERROR-336 | 데이터 요청은 한 번에 최대 1000건 |
| ERROR-500 | 서버 오류 |
| ERROR-600 | DB 연결 오류 |
| ERROR-601 | SQL 오류 |

## 2. 페이징 방식

**INDEX 기반** (START_INDEX / END_INDEX, 최대 1000건 차이). 날짜 기반 아님.

⚠️ **실측 필요**: 명세서에는 START_INDEX/END_INDEX로 여러 건 조회가 가능하다고 되어 있으나,
과거 다른 서울시 API에서 명세서와 달리 실제로는 최신 1건만 반환되는 사례가 있었음.
Claude Code는 로컬 테스트 단계에서 실제 키로 `START_INDEX=1, END_INDEX=5` 등으로 호출해
`list_total_count`(또는 응답 내 유사 필드)와 실제 반환 건수를 반드시 실측하고 DEVLOG.md에 기록할 것.

## 3. MCP 툴 설계 (최소 개수)

**툴 1개만 사용**:

### `get_individual_land_price`
- 설명: 서울시 개별공시지가(원/㎡)를 시군구명·기준년도 기준으로 조회. 법정동명/본번/부번/필지구분코드로 세부 필터링 가능.
- 파라미터:
  - `sigungu_nm` (str, 필수) — 시군구명, 예: "종로구"
  - `year` (str, 필수) — 기준년도 YYYY, 예: "2020"
  - `bjdong_nm` (str, 선택, 기본값 "") — 법정동명
  - `bonbeon` (str, 선택, 기본값 "") — 본번 (0~9999)
  - `bubeon` (str, 선택, 기본값 "") — 부번 (0~9999)
  - `pilgi_cd` (str, 선택, 기본값 "") — 필지구분코드 (1~9)
  - `start_index` (int, 기본값 1)
  - `end_index` (int, 기본값 100) — start_index와 차이 1000 이하
- 반환: 개별 필지별 시군구명/법정동명/본번/부번/필지구분명/기준년월/공시지가(원/㎡)/기준년도 리스트

## 4. 기술 스택

- Python 3.11+
- fastmcp (MCP 서버 프레임워크)
- httpx (비동기 HTTP 클라이언트)
- python-dotenv (.env 로드, BOM 없이 저장 — PowerShell 스크립트가 처리)
- 배포: Docker + fly.io

## 5. 디렉토리 구조

```
seoul-individual-land-price-mcp/
├── server.py              # MCP 서버, 툴 정의
├── seoul_api.py            # 서울 열린데이터광장 API 호출 + 에러코드 매핑
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── fly.toml
├── README.md
├── DEVLOG.md
└── CLAUDE.md
```

## 6. 진행 순서

1. Claude Code가 `CLAUDE.md`를 읽고 이 `DEVPLAN.md` 기준으로 구현 시작
2. requirements.txt → seoul_api.py → server.py → .env.example/.gitignore
3. 로컬 테스트 (실제 키로 호출, START_INDEX/END_INDEX 실측 포함)
4. FastMCP 스모크 테스트 (initialize까지)
5. Dockerfile/fly.toml 작성
6. README/DEVLOG 갱신 후 git commit/push
7. 여기서 정지 — 사용자가 fly launch/secrets/deploy를 직접 실행

## 7. 사용자가 먼저 할 일

1. 서울 열린데이터광장에서 인증키 발급 (이미 있다면 생략)
2. 이 문서 4개(DEVPLAN.md, CLAUDE.md, README.md, DEVLOG.md)를 `DocsPath` 폴더에 저장
3. `new-mcp-project.ps1` 스크립트 실행 (프로젝트 지침 4번 안내 문구 참고)
