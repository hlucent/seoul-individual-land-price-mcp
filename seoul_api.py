import os
from urllib.parse import quote

import httpx

BASE_URL = "http://openapi.seoul.go.kr:8088"
SERVICE = "IndividuallyPostedLandPriceService"

ERROR_MESSAGES = {
    "INFO-100": "인증키가 유효하지 않습니다.",
    "INFO-200": "해당하는 데이터가 없습니다.",
    "ERROR-300": "필수 값이 누락되었습니다.",
    "ERROR-301": "TYPE 값이 누락되었거나 유효하지 않습니다.",
    "ERROR-310": "해당 서비스를 찾을 수 없습니다 (SERVICE 확인).",
    "ERROR-331": "START_INDEX 값이 올바르지 않습니다.",
    "ERROR-332": "END_INDEX 값이 올바르지 않습니다.",
    "ERROR-333": "요청위치 값이 정수가 아닙니다.",
    "ERROR-334": "START_INDEX가 END_INDEX보다 큽니다.",
    "ERROR-335": "샘플데이터는 한 번에 최대 5건까지만 요청 가능합니다.",
    "ERROR-336": "데이터 요청은 한 번에 최대 1000건까지만 가능합니다.",
    "ERROR-500": "서버 오류가 발생했습니다.",
    "ERROR-600": "DB 연결 오류가 발생했습니다.",
    "ERROR-601": "SQL 오류가 발생했습니다.",
}


class SeoulApiError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


async def fetch_individual_land_price(
    sigungu_nm: str,
    year: str,
    bjdong_nm: str = "",
    bonbeon: str = "",
    bubeon: str = "",
    pilgi_cd: str = "",
    start_index: int = 1,
    end_index: int = 100,
) -> dict:
    api_key = os.environ["SEOUL_API_KEY"]

    # 실측 결과: 이 API는 BJDONG_NM/BONBEON/BUBEON/PILGI_CD를 빈 문자열로 비워두면
    # ERROR-500(서버 오류)을 반환한다. 네 값을 모두 채우거나 모두 비워야 한다.
    optional_params = {
        "bjdong_nm": bjdong_nm,
        "bonbeon": bonbeon,
        "bubeon": bubeon,
        "pilgi_cd": pilgi_cd,
    }
    filled = {k: v for k, v in optional_params.items() if v != ""}
    if filled and len(filled) != len(optional_params):
        missing = [k for k, v in optional_params.items() if v == ""]
        raise SeoulApiError(
            "ERROR-CLIENT-PARTIAL-PARAMS",
            "bjdong_nm/bonbeon/bubeon/pilgi_cd는 모두 채우거나 모두 비워야 합니다 "
            f"(비어 있는 값: {', '.join(missing)}). 일부만 채우면 서울시 API가 ERROR-500을 반환합니다.",
        )

    path_parts = [
        api_key,
        "json",
        SERVICE,
        str(start_index),
        str(end_index),
        sigungu_nm,
        bjdong_nm,
        str(bonbeon) if bonbeon != "" else "",
        str(bubeon) if bubeon != "" else "",
        pilgi_cd,
        year,
    ]
    encoded_parts = [quote(part, safe="") for part in path_parts]
    url = BASE_URL + "/" + "/".join(encoded_parts)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    service_result = data.get(SERVICE)
    if service_result is None:
        # 인증키 오류 등은 SERVICE 키 없이 RESULT만 최상위에 오는 경우가 있음
        result = data.get("RESULT")
        if result:
            code = result.get("CODE", "ERROR-UNKNOWN")
            message = result.get("MESSAGE", ERROR_MESSAGES.get(code, "알 수 없는 오류"))
            raise SeoulApiError(code, message)
        raise SeoulApiError("ERROR-UNKNOWN", f"예상치 못한 응답 형식: {data}")

    result = service_result.get("RESULT", {})
    code = result.get("CODE", "")
    if code and code != "INFO-000":
        message = result.get("MESSAGE", ERROR_MESSAGES.get(code, "알 수 없는 오류"))
        raise SeoulApiError(code, message)

    return {
        "list_total_count": service_result.get("list_total_count", 0),
        "rows": service_result.get("row", []),
    }
