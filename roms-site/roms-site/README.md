# ROMS 해양 예측 조회 사이트

국립해양조사원 ROMS 수치예측모델 조회 API(공공데이터포털)를 사용해 좌표별 수온·유향·유속 예측을 지도, 그래프, 표로 보여 주는 사이트입니다.

## 구성
- `index.html` 화면 (지도·차트·표·CSV 저장)
- `server.py` 인증키를 숨겨 주는 프록시 서버 (외부 패키지 없음)
- `render.yaml` Render 배포 설정

브라우저에서 공공데이터포털을 직접 부르면 CORS 때문에 막히고 인증키도 노출됩니다. 그래서 서버가 대신 호출합니다.

## 내 컴퓨터에서 실행
`.env` 파일에 인증키가 이미 들어 있어 아래 한 줄이면 실행됩니다. `.env`는 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다.
```bash
python server.py
```
인증키를 환경변수로 직접 지정하려면:
```bash
# Windows PowerShell:  $env:ROMS_API_KEY="발급받은_인증키"
export ROMS_API_KEY="발급받은_인증키"
python server.py
# http://localhost:8000
```

## 누구나 접속하는 링크로 배포 (Render, 무료 플랜 가능)
1. 이 폴더를 GitHub 저장소로 올립니다.
2. Render에서 New > Web Service > 저장소 선택 (render.yaml 자동 인식).
3. Environment에 `ROMS_API_KEY` 값으로 인증키를 입력하고 배포합니다.
4. 발급되는 `https://...onrender.com` 주소를 공유하면 됩니다.

인증키는 코드나 저장소에 넣지 말고 환경변수로만 설정하세요.

## API 사용 제한 (명세서 기준)
- 위도·경도 범위는 각각 최대 1도, 한 페이지 최대 300건
- 현재 일자 기준 8일간 예측 제공
