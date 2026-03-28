# Off-Book-Search

오프라인 서점 통합 재고 검색 앱. 책을 검색하면 알라딘 중고매장, 교보문고, 영풍문고의 오프라인 매장 재고를 한 번에 조회한다.

## 문제

책을 오프라인으로 바로 구매하려면 각 서점 홈페이지에 하나하나 접속해서 근처 매장의 재고를 확인해야 한다. 이 앱은 한 번의 검색으로 3개 서점의 오프라인 재고를 통합 조회해준다.

## 기술 스택

- **Backend**: Python 3.12, FastAPI, httpx (async)
- **Frontend**: Jinja2 + Tailwind CSS (CDN)
- **책 검색**: 카카오 책 검색 API
- **재고 조회**: 서점별 API/스크래핑 (아래 Provider별 설명 참고)
- **캐싱**: cachetools (in-memory TTL cache)

## 실행 방법

```bash
# 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# API 키 설정
cp .env.example .env
# .env 파일에 KAKAO_API_KEY, ALADIN_TTB_KEY 입력

# 서버 실행
uvicorn app.main:app --reload

# 테스트
pytest tests/ -v
```

## 아키텍처

```
User Browser
    |
    v
FastAPI (app/main.py)
    |
    +---> GET /api/search?q=  -----> 카카오 책 검색 API → BookSearchResult 리스트
    |
    +---> GET /api/inventory/{isbn13} → InventoryAggregator (asyncio.gather)
              |
              +---> AladinProvider     (알라딘 TTB OpenAPI)
              +---> KyoboProvider      (교보문고 kiosk SSR 파싱)
              +---> YoungpoongProvider (영풍문고 REST API, guest 토큰)
              |
              v
          AggregatedInventory (서점별 매장명, 재고 수량, 서가 위치)
```

검색과 재고 조회는 별도 엔드포인트로 분리되어 있다. 검색은 ~200ms로 빠르고, 재고 조회는 3개 서점을 병렬로 호출하므로 최대 10초까지 걸릴 수 있다. 프론트엔드는 검색 결과를 먼저 표시한 뒤, "오프라인 재고 확인" 버튼 클릭 시 AJAX로 재고를 비동기 로딩한다.

## 디렉토리 구조

```
app/
├── main.py                  # FastAPI 앱, lifespan, 라우터, 템플릿 페이지
├── config.py                # pydantic-settings (API 키, 타임아웃, 캐시 TTL)
├── api/routes/
│   ├── search.py            # GET /api/search?q=
│   ├── inventory.py         # GET /api/inventory/{isbn13}
│   └── health.py            # GET /api/health
├── models/
│   ├── book.py              # BookSearchResult, BookSearchResponse
│   └── inventory.py         # StoreStock, ProviderResult, AggregatedInventory
├── services/
│   ├── book_search.py       # 카카오 책 검색 API 래퍼
│   └── inventory_aggregator.py  # asyncio.gather로 Provider 병렬 호출
├── providers/
│   ├── base.py              # BaseProvider ABC
│   ├── aladin.py            # 알라딘 중고매장 (공식 TTB API)
│   ├── kyobo.py             # 교보문고 (kiosk.kyobobook.co.kr SSR 파싱)
│   └── youngpoong.py        # 영풍문고 (guest 토큰 + REST API)
├── cache/
│   └── memory.py            # TTLCache (검색 24h, 재고 30m)
└── templates/               # Jinja2 + Tailwind
    ├── base.html
    ├── index.html
    └── results.html
```

## Provider별 재고 조회 방식

### 알라딘 중고매장

공식 TTB OpenAPI 사용. `ALADIN_TTB_KEY` 필요.

- `GET http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx?ttbkey={key}&itemIdType=ISBN13&ItemId={isbn}&output=js`
- ISBN으로 바로 중고매장 재고 조회, JSON 응답

### 교보문고

교보문고 무인안내 키오스크 페이지(kiosk.kyobobook.co.kr)를 매장별로 병렬 요청하여 SSR HTML에서 재고 데이터를 파싱한다. 별도 API 키 불필요.

- `GET https://kiosk.kyobobook.co.kr/bookInfoInk?site={storeCode}&barcode={isbn}&ejkGb=KOR`
- HTML 내 `self.__next_f.push` 스크립트에서 JSON 추출 (이중 이스케이프 디코딩)
- 서울 주요 16개 매장을 `asyncio.gather`로 병렬 조회
- 재고 수량 + 서가 위치(관, 서가번호, 분류명) 제공

### 영풍문고

영풍문고 REST API를 3단계로 호출한다. 별도 API 키 불필요.

1. **Guest 토큰 획득**: `PUT /back_login/base_login/api/v1/auth/login-guest`
2. **ISBN → bookCd 변환**: `GET /back_shop/base_shop/api/v1/search_indexes/result/product?query={isbn}`
3. **매장별 재고 조회**: `GET /back_shop/base_shop/api/v1/product/stock-info?iBookCd={bookCd}`

모든 요청에 `clientId`, `accessToken` 헤더 필수. 44개 전 매장 재고를 1회 API 호출로 조회.

## API 응답 형식

```jsonc
// GET /api/inventory/{isbn13}
{
  "isbn13": "9788954442695",
  "results": [
    {
      "provider": "aladin",
      "display_name": "알라딘 중고매장",
      "status": "success",  // "success" | "error" | "timeout"
      "stores": [
        { "store_name": "알라딘 강남점", "has_stock": true, "quantity": 3 }
      ]
    },
    {
      "provider": "kyobo",
      "display_name": "교보문고",
      "status": "success",
      "stores": [
        { "store_name": "교보문고 광화문점", "has_stock": true, "quantity": 11, "location": "J관 21 판타지/SF" }
      ]
    },
    {
      "provider": "youngpoong",
      "display_name": "영풍문고",
      "status": "success",
      "stores": [
        { "store_name": "영풍문고 가산마리오", "has_stock": true, "quantity": 5 }
      ]
    }
  ],
  "total_stores_with_stock": 15
}
```

## 환경 변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `KAKAO_API_KEY` | O | 카카오 REST API 키 (책 검색) |
| `ALADIN_TTB_KEY` | O | 알라딘 TTB API 키 (중고매장 재고) |
