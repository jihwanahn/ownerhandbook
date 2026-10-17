# 참모장 핸드오프 — 2026-10-18 (런 083687b3, 미완료분)

이 런은 **이슈에 묶이지 않은 수동 실행**(run.contextSnapshot에 issueId 없음)이라
Paperclip의 cross-issue 가드가 **모든 이슈 댓글/수정을 403으로 거부**했습니다
(근거: `@paperclipai/server` `services/cross-issue-influence-limit.js` —
`readRunSourceIssueId(run.contextSnapshot)`가 null이면 차단).

그래서 대표님께는 **JHL-1 인터랙션 카드**(`d7e796e3`, kind=ask_user_questions, pending)로
요청 사항을 전달했습니다. 아래 두 텍스트는 **유효한 런 컨텍스트가 있는 다음 실행**에서
그대로 댓글로 올리면 됩니다.

## 상태 메모 (이 런에서 바뀐 것)
- JHL-1: 체크아웃→릴리스 부작용으로 상태가 `in_review` → `todo`가 됨. 다음 런에서 댓글 올린 뒤 `in_review`로 되돌릴 것(카드 답변 대기 상태이므로).
- JHL-1 카드 `d7e796e3` (pending, ask_user_questions, wake_assignee) — 대표님이 답하면 재개됨.
- JHL-1에 `issue_commented` 웨이크(2026-10-17T17:20:45Z)가 **deferred** 상태였고, 이 런의 릴리스로 실행 락은 풀렸음 → 다음 런이 이 댓글 컨텍스트로 뜰 가능성이 높음.
- 테마 라이브 = `owners-handbook-v2-decl.xml` (검증 완료, 위젯 미렌더 지속).
- `bisect/B0-probe.xml` 추가·커밋(`e9b55b7`) — 대표님 요청용 진단 파일.

---

## (A) JHL-1에 올릴 댓글 (다음 유효 런에서)

## 레이아웃 확인 잘 받았습니다 — 원인이 좁혀졌고, 이번 한 번(2~6분)이면 방향이 확정됩니다

대표님, **섹션 5개(헤더/Navigation/Posts/사이드바/바닥글)는 있는데 위젯 상자가 없는** 레이아웃 — 그 정보가 결정적이었습니다. 제 쪽 실측과 합치면:

- **확정**: Blogger의 "레이아웃"(가젯 배치)에 **우리 테마의 위젯이 만들어지지 않은 상태**입니다. 그래서 블로그가 빕니다. 테마 파일 자체는 정상 적용·검증 완료(화면 코드 구조·SEO·모바일 정상) — 문제는 "Blogger가 위젯을 그려주지 않는 것" 하나입니다.
- 원인 후보는 두 갈래로 좁혀졌습니다: (가) **적용 경로** — 붙여넣기로는 레이아웃이 재구성되지 않아서 (나) **테마 파일** — Blogger가 이 파일의 위젯 선언을 처리하지 못해서. 아래 ①②로 이 둘을 한 번에 가릅니다.
- 같은 증상은 Blogger에서 알려진 실패 유형이고(위젯이 '등록'은 되는데 화면에 안 그려짐), 공식 커뮤니티의 표준 해결법이 **최소 테마로 진단(bisect)** 입니다. 그래서 진단 파일을 준비했습니다.

### 부탁 ① — 업로드 한 번 (2분, 먼저)
지난번에 **붙여넣기**로만 하셨다면, 이번엔 **정식 경로**로 한 번만요:
1. 테마 → **⋮ → 백업/복원 → 업로드** → `E:\ownerhandbook\blogger\theme\owners-handbook-v2-decl.xml` 선택
2. **성공하면**: 블로그 새 탭 → Ctrl+F5 → **위젯(제목·메뉴)이 보이는지** 한 줄. → 보이면 끝입니다.
3. **거부되면**: 뜬 문구 **그대로** 한 줄 (기존 테마는 그대로 유지되니 안전) → 아래 ②로.

### 부탁 ② — 진단 테마 붙여넣기 (3분, ①이 거부됐거나 ①성공에도 여전히 빈 경우)
`E:\ownerhandbook\blogger\theme\bisect\B0-probe.xml`
1. 테마 → ⋮ → **HTML 편집** → **Ctrl+A → Delete** → 메모장으로 위 파일을 **새로 열어** Ctrl+A → Ctrl+C → 편집창 **Ctrl+V** → **저장**
2. 블로그 새 탭 → **Ctrl+F5** → 아래 문구가 보이는지 확인:
   - `B0-MARKER-WIDGET-RENDERED` (기존 위젯이 그려지는가)
   - `B0-PROBE-FRESH-WIDGET-RENDERED` / `B0-PROBE-FRESH-CONTENT` / `B0-PROBE-BARE-FRESH-CONTENT` (새 위젯도 만들어지는가)
   - `글 없음` 같은 기본 Blogger 내용
3. **보인 문구 그대로 한 줄** (또는 "아무것도 안 보임")
*일부러 디자인 없는 임시 테마입니다(정상). 되돌리기는 다음 안내에서 v1 파일로 한 번에 — 지금은 그대로 두세요.*

### 부탁 ③ — 레이아웃 화면 스크린샷 (1분)
Win+Shift+S로 레이아웃 화면 캡처 → 이 댓글에 붙여넣기(Ctrl+V). 제가 직접 보면 다음 판단이 확실해집니다.

### 참고 — 병행 제안
테마가 길어질 수 있으니, **첫 글 준비(초안→검수→공개)를 테마와 무관하게 먼저 시작**하시는 것도 추천드립니다(GitHub 이미지 호스팅 연결 10분 → 첫 글). 원하시면 다음 댓글에서 그 절차를 안내드리겠습니다 — 어느 쪽이든 편하신 대로 말씀만 주세요.

— 참모장

(※ 이번 런에서는 위 요청을 JHL-1의 **인터랙션 카드**로도 전달해 두었습니다. 카드 답변이 오면 이 댓글은 생략해도 됩니다.)

---

## (B) JHL-4에 올릴 엔지니어 지시 (다음 유효 런에서)

## 참모장 — 대표님 회신 접수 + 라이브 재실측 + 다음 산출물 지시 (B0-probe 준비 완료)

대표님 회신(JHL-1 `8057897d`): **"레이아웃에는 섹션 5개(헤더/Navigation/Posts/사이드바/바닥글)만 보이고, 블로그는 여전히 빔."** → `PLAN.md` 관찰①의 답은 "가젯 상자 없음"입니다. 다음 분기(3단계 B0)가 본선입니다.

### 1) 이번 런 라이브 재실측 (제 손, 캐시버스터)
| 관찰 | 값 |
|---|---|
| `_RegisterWidget` | **6** — Header1('header'), PageList1('nav'), Blog1('main-posts'), HTML1('sidebar'), PageList2('footer'), HTML2('footer') |
| `BlogSearch1` | **0** (10-16 시점의 7번째 등록은 현재 없음) |
| `no-items section` | 5 / 위젯 wrapper **0** / `id='Label1'·'Label2'` **0** |
| SetDataContext `'widgets'` 항목 | **없음** (대조군에는 있음) |

→ 등록 6건의 섹션 id가 우리 테마의 섹션 id와 정확히 일치합니다. 즉 등록 블록은 우리 테마 기준으로 생성돼 있고, 결론은 "테마는 인식, 위젯은 미생성". 대표님 관찰("레이아웃에 위젯 상자 없음")과 정합합니다.

### 2) 산출물 — `bisect/B0-probe.xml` (커밋 `e9b55b7`, 제가 준비)
B0-baseline에 **프로브 2개**를 추가했습니다(새 id라 레이아웃에 인스턴스가 존재할 수 없음):
- 섹션 `jhl-probe` + 위젯 `HTML99`(커스텀 인클루더블+설정) → `B0-PROBE-FRESH-WIDGET-RENDERED` / `B0-PROBE-FRESH-CONTENT`
- 위젯 `HTML98`(bare — 커스텀 인클루더블 없음 → 기본 마크업 경로) → `B0-PROBE-BARE-FRESH-CONTENT`

한 번의 붙여넣기로 **"기존 id 재매핑"과 "새 위젯 인스턴스화"를 동시에** 가릅니다. well-formed 확인·`verify_theme.py` 실행 확인(진단 테마 특성상 일부 FAIL은 정상 — `[2c]` version 균일성 항목 포함). 대표님께는 **①업로드 재시도 → ②B0-probe 붙여넣기 → ③스크린샷** 순으로 안내했습니다.

### 3) 지시 — 다음 산출물 2건 준비 부탁
1. **B0-probe 검토·편입**: 설계 이견 있으면 코멘트로, 없으면 검증기/테스트에 편입해 B0와 동일 취급해 주세요.
2. **v3-선언 변형(조건부 1순위)**: B0-probe가 "아무것도 안 보임"이면 본선입니다. 근거 — 동작하는 현대 테마(Contempo 원본 XML·techjet)는 전부 `<html b:layoutsVersion='3' b:defaultwidgetversion='2' …>` + `]]></b:skin>` 뒤 **`<b:defaultmarkups>`(13블록)** + 위젯별 **전체 인클루더블 세트(대부분 빈 태그)** 를 선언합니다. SO 50086387은 "`b:defaultwidgetversion='2'`를 쓰려면 defaultmarkups를 함께 넣어야 위젯이 갱신된다"고 명시 — 우리 파일은 `defaultwidgetversion='2'`만 있고 **defaultmarkups가 없습니다.** "변수 하나" 원칙으로 2파일 분리해 주세요(① layoutsVersion+defaultmarkups만 추가 ② 데이터 태그 v3화).
3. 검증기 `[2c]`의 `no b:layoutsVersion='3'` 항목은 위 변형 전용 예외 규칙으로 조정 부탁드립니다.

이견 있으면 근거와 함께 반대해 주세요. 대표님 결과 오는 대로 재검증 값과 함께 이어서 지시하겠습니다.
