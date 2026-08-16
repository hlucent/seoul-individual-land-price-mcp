# 서울시 개별공시지가 정보 MCP

서울 열린데이터광장의 [서울시 개별공시지가 정보(IndividuallyPostedLandPriceService)](http://data.seoul.go.kr/)를
MCP 툴로 제공하는 서버입니다. 시군구명·기준년도(+ 법정동/본번/부번/필지구분코드)로
개별 필지의 공시지가(원/㎡)를 조회합니다.

## 제공 툴

### `get_individual_land_price`
시군구명과 기준년도로 개별공시지가를 조회합니다. 법정동명/본번/부번/필지구분코드로 추가 필터링 가능.

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| sigungu_nm | string | 필수 | 시군구명 (예: 종로구) |
| year | string | 필수 | 기준년도 (YYYY) |
| bjdong_nm | string | 선택 | 법정동명 |
| bonbeon | string | 선택 | 본번 (0~9999) |
| bubeon | string | 선택 | 부번 (0~9999) |
| pilgi_cd | string | 선택 | 필지구분코드 (1:토지 2:임야 3:가지번 4:가지번(부분세분) 5:블럭지번 6:블럭지번(롯트세분) 7:블럭지번(지구) 8:블럭지번(지구-롯트) 9:기타지번) |
| start_index | integer | 선택 (기본 1) | 조회 시작 위치 |
| end_index | integer | 선택 (기본 100) | 조회 종료 위치 (start_index와 차이 최대 1000) |

응답 필드: 시군구명/시군구코드/법정동명/법정동코드/본번/부번/필지구분명/필지구분코드/
기준년월/**공시지가(원/㎡)**/기준년도

## 설치 및 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # SEOUL_API_KEY 값 입력 (BOM 없이 저장할 것)
python server.py
```

## 환경변수

| 이름 | 설명 |
|---|---|
| `SEOUL_API_KEY` | 서울 열린데이터광장에서 발급받은 인증키 |
| `PORT` | 서버 포트 (기본값은 server.py 참고) |

## 배포 (fly.io)

```bash
fly launch --no-deploy
fly secrets set SEOUL_API_KEY=발급받은키
flyctl deploy
```

배포 후 Claude.ai > 설정 > 커넥터에서 연결하고, "사용 가능한 도구" 목록에 툴이 뜨는지 확인하세요.

## 라이선스 / 출처

- 원데이터: 서울특별시 (도시공간본부 토지관리과)
- 이용허락조건: **공공누리 1유형** (출처표시, 상업적 이용 및 변경 가능)
- 출처 표기 예: "본 서비스는 서울열린데이터광장의 개별공시지가 정보를 사용합니다."
