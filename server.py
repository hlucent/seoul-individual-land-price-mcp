import os
import time
from collections import defaultdict, deque
from threading import Lock

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

from seoul_api import fetch_individual_land_price, SeoulApiError

load_dotenv()

mcp = FastMCP("seoul-individual-land-price")


# --- Rate limiting (in-memory, 단일 프로세스 기준) ---
#
# 규칙:
#   1. 같은 IP 기준 분당 3회 초과 요청 시 429
#   2. 1시간 내 429를 5회 이상 받은 IP는 이후 24시간 차단
#   3. IP당 일일(rolling 24h) 총 호출 30회 초과 시 429
#
# fly.io는 머신을 여러 대 띄울 수 있어 프로세스 간 상태 공유가 안 되므로
# 완벽한 전역 제한은 아니지만(CLAUDE.md 지침에 따라 in-memory로 충분), 단일 요청
# 경로(MCP 툴 호출)에 대한 기본적인 남용 방지 목적으로는 충분하다.
RATE_LIMIT_PER_MINUTE = 3
RATE_LIMIT_WINDOW_SECONDS = 60
BLOCK_THRESHOLD_429_COUNT = 5
BLOCK_THRESHOLD_WINDOW_SECONDS = 3600
BLOCK_DURATION_SECONDS = 24 * 3600
DAILY_LIMIT = 30
DAILY_WINDOW_SECONDS = 24 * 3600

_lock = Lock()
_minute_times: dict[str, deque] = defaultdict(deque)
_daily_times: dict[str, deque] = defaultdict(deque)
_429_times: dict[str, deque] = defaultdict(deque)
_blocked_until: dict[str, float] = {}


def _get_client_ip() -> str:
    try:
        request = get_http_request()
    except RuntimeError:
        return "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _record_429(ip: str, now: float) -> None:
    """Must be called while holding _lock."""
    times_429 = _429_times[ip]
    while times_429 and now - times_429[0] > BLOCK_THRESHOLD_WINDOW_SECONDS:
        times_429.popleft()
    times_429.append(now)
    if len(times_429) >= BLOCK_THRESHOLD_429_COUNT:
        _blocked_until[ip] = now + BLOCK_DURATION_SECONDS


def _check_rate_limit(ip: str) -> None:
    """Raises ToolError (mapped to a 429-equivalent MCP error) if the ip is rate limited."""
    now = time.monotonic()

    with _lock:
        blocked_until = _blocked_until.get(ip)
        if blocked_until is not None:
            if now < blocked_until:
                raise ToolError("429: 반복적인 요청 한도 초과로 24시간 동안 차단되었습니다.")
            del _blocked_until[ip]

        minute_times = _minute_times[ip]
        while minute_times and now - minute_times[0] > RATE_LIMIT_WINDOW_SECONDS:
            minute_times.popleft()

        daily_times = _daily_times[ip]
        while daily_times and now - daily_times[0] > DAILY_WINDOW_SECONDS:
            daily_times.popleft()

        if len(minute_times) >= RATE_LIMIT_PER_MINUTE:
            _record_429(ip, now)
            raise ToolError("429: 요청 한도를 초과했습니다 (분당 3회 초과).")

        if len(daily_times) >= DAILY_LIMIT:
            _record_429(ip, now)
            raise ToolError("429: 일일 요청 한도를 초과했습니다 (하루 30회 초과).")

        minute_times.append(now)
        daily_times.append(now)


class RateLimitMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        ip = _get_client_ip()
        _check_rate_limit(ip)
        return await call_next(context)


mcp.add_middleware(RateLimitMiddleware())


@mcp.tool()
async def get_individual_land_price(
    sigungu_nm: str,
    year: str,
    bjdong_nm: str = "",
    bonbeon: str = "",
    bubeon: str = "",
    pilgi_cd: str = "",
    start_index: int = 1,
    end_index: int = 100,
) -> dict:
    """서울시 개별공시지가(원/㎡)를 시군구명·기준년도 기준으로 조회한다.

    법정동명/본번/부번/필지구분코드로 세부 필터링이 가능하다.

    주의(실측 확인): bjdong_nm/bonbeon/bubeon/pilgi_cd는 넷 다 비우거나 넷 다 채워야 한다.
    일부만 채우면 서울시 API가 ERROR-500(서버 오류)을 반환한다.

    Args:
        sigungu_nm: 시군구명 (필수), 예: "종로구"
        year: 기준년도 YYYY (필수), 예: "2020"
        bjdong_nm: 법정동명 (선택, 기본값 ""). 채우려면 bonbeon/bubeon/pilgi_cd도 함께 채워야 함
        bonbeon: 본번 0~9999 (선택, 기본값 ""). 채우려면 bjdong_nm/bubeon/pilgi_cd도 함께 채워야 함
        bubeon: 부번 0~9999 (선택, 기본값 ""). 채우려면 bjdong_nm/bonbeon/pilgi_cd도 함께 채워야 함
        pilgi_cd: 필지구분코드 1~9 (선택, 기본값 ""). 채우려면 bjdong_nm/bonbeon/bubeon도 함께 채워야 함.
            1:토지, 2:임야, 3:가지번, 4:가지번(부분세분), 5:블럭지번,
            6:블럭지번(롯트세분), 7:블럭지번(지구), 8:블럭지번(지구-롯트), 9:기타지번
        start_index: 요청 시작 위치, 1부터 (기본값 1)
        end_index: 요청 종료 위치, start_index와 차이 1000 이하 (기본값 100)

    Returns:
        dict:
            list_total_count (int): 전체 결과 건수
            rows (list[dict]): 필지별 결과 목록. 각 항목 필드:
                - SIGUNGU_NM: 시군구명
                - SIGUNGU_CD: 시군구코드
                - BJDONG_NM: 법정동명
                - BJDONG_CD: 법정동코드
                - BONBEON: 본번
                - BUBEON: 부번
                - PILGI_NM: 필지구분명
                - PILGI_CD: 필지구분코드
                - BASE_MON: 기준년월
                - JIGA: 공시지가 (단위: 원/㎡)
                - YEAR: 기준년도 (YYYY)
    """
    try:
        return await fetch_individual_land_price(
            sigungu_nm=sigungu_nm,
            year=year,
            bjdong_nm=bjdong_nm,
            bonbeon=bonbeon,
            bubeon=bubeon,
            pilgi_cd=pilgi_cd,
            start_index=start_index,
            end_index=end_index,
        )
    except SeoulApiError as e:
        return {"error_code": e.code, "error_message": e.message}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
