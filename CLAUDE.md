# CLAUDE.md — 서울시 개별공시지가 정보 MCP (Claude Code 실행 지침)

## 절대 규칙

- **DEVPLAN.md 하나만 먼저 읽고 시작한다.** 다른 문서 재탐색 금지.
- **웹서치 금지.** API 스펙은 DEVPLAN.md에 이미 정리되어 있음.
- 불확실한 부분은 추측성 재설계 대신 **기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"**로 기록.
- 동일 오류는 **최대 3회까지만 재시도**. 3회 실패 시 기록하고 사용자에게 보고 후 중단.
- **`flyctl deploy`와 `fly logs`는 절대 스스로 실행하지 않는다.** 출력이 길어 토큰을 많이 소모함. 배포 준비가 끝나면 안내 문구만 출력하고 멈춘다.

## 기술적으로 반드시 적용할 것 (과거 실패 원인 → 재발 방지)

### `.env` 관련
`.env` 파일을 직접 생성하거나 점검하는 코드를 작성할 때, BOM(Byte Order Mark) 때문에
`python-dotenv`가 키를 못 읽는 문제가 과거에 있었음. `.env`는 PowerShell 스크립트가
BOM 없이 이미 생성해두므로, Claude Code는 이 파일을 새로 덮어쓰지 말고 존재 여부만 확인할 것.
만약 직접 `.env.example`을 만들 때는 UTF-8(BOM 없음)로 저장한다.

### `server.py`의 `mcp.run()`은 항상 `stateless_http=True` 포함

```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
```

**이유**: fly.io는 기본적으로 머신을 2대(고가용성) 띄운다. streamable-http 세션이 프로세스
인메모리에만 저장되면 fly proxy가 요청을 다른 머신으로 라우팅할 때 세션을 모르는 머신이
404를 반환한다. 게다가 `auto_stop_machines`로 머신이 재시작되면 세션이 전부 사라진다.
처음부터 stateless로 만들면 이 문제 자체가 발생하지 않는다.

**이 옵션 없이 배포하면 Claude.ai 커넥터에서 "사용 가능한 도구 없음"으로 보이는 문제가
발생했던 전례가 있으므로 절대 빠뜨리지 않는다.**

## 작업 순서

1. `requirements.txt` — `fastmcp`, `httpx`, `python-dotenv`
2. `seoul_api.py` — API 호출 + 에러코드 매핑 (DEVPLAN.md의 에러 코드 표 그대로 반영)
3. `server.py` — 툴 정의(DEVPLAN.md 기준 `get_individual_land_price` 1개), docstring에
   **응답 필드와 단위(공시지가는 원/㎡)를 반드시 명시**. `stateless_http=True` 필수 반영.
   - 경로 파라미터 조립 시 선택 파라미터(BJDONG_NM/BONBEON/BUBEON/PILGI_CD)를 생략하지 말고
     빈 문자열로 자리를 채워서 URL 경로 순서를 유지할 것 (DEVPLAN.md 1절 참고).
4. `.env.example`, `.gitignore` 작성
5. 로컬 테스트 — 실제 키로 각 파라미터 조합 호출, **START_INDEX/END_INDEX로 실제 여러 건이
   반환되는지 실측 확인**(과거 다른 서울시 API에서 명세서와 달리 최신 1건만 반환된 사례
   있음). 결과를 DEVLOG.md에 기록.
6. FastMCP 서버 스모크 테스트 (initialize 요청까지만 — 세션 재사용 시나리오는 배포 후 검증)
7. `Dockerfile`, `fly.toml` 작성
8. README.md/DEVLOG.md 갱신
9. `git add/commit/push`까지 수행
10. **여기서 정지** — 아래 "사용자 안내 문구"를 그대로 출력하고 대기

## 사용자 안내 문구 (작업 완료 후 출력)

```
개발이 끝나고 Claude Code가 멈추면, 아래 3줄을 직접 실행하세요 (토큰 절약을 위해 자동 실행 안 함):
   fly launch --no-deploy
   fly secrets set SEOUL_API_KEY=발급받은키
   flyctl deploy

배포 후 Claude.ai > 설정 > 커넥터 에서 이 MCP를 연결/재연결하고
"사용 가능한 도구" 목록에 툴이 뜨는지 반드시 확인하세요.
```

## 하지 말 것

- 툴 개수를 DEVPLAN.md 범위(1개)보다 늘리지 않기
- 인증키 하드코딩 금지 — 반드시 `os.environ["SEOUL_API_KEY"]`로 읽기
- `stateless_http=True` 누락 금지
- `flyctl deploy` / `fly logs` 자동 실행 금지
- 매 파일 생성마다 개별 승인이 반복되면, 사용자에게 "이번 세션 전체 편집 허용"으로 넘어가라고
  첫 승인 시점에 안내. 단, 실제 API 키로 네트워크 호출하는 `python -c` 류는 매번 개별 확인 권장.
