import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from seoul_api import fetch_individual_land_price, SeoulApiError

load_dotenv()

mcp = FastMCP("seoul-individual-land-price")


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

    Args:
        sigungu_nm: 시군구명 (필수), 예: "종로구"
        year: 기준년도 YYYY (필수), 예: "2020"
        bjdong_nm: 법정동명 (선택, 기본값 "")
        bonbeon: 본번 0~9999 (선택, 기본값 "")
        bubeon: 부번 0~9999 (선택, 기본값 "")
        pilgi_cd: 필지구분코드 1~9 (선택, 기본값 "").
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
