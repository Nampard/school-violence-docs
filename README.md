# 학교폭력 행정서류 생성 스킬 (school-violence-docs)

학교폭력 사안 처리 흐름에 따라 **실제 내용을 채운** 한글(hwpx) 행정문서를 생성하는 AI 스킬입니다.
빈 양식을 나눠주는 것이 아니라, 담당자가 두서없이 설명한 사안 정황을 양식의 정확한 칸에 채워 출력합니다.
채우기 어려운 칸은 비워 두므로, 담당자는 아래아한글에서 빈칸만 마무리하면 됩니다.

> ⚠️ **적용 범위**
> - 본 스킬의 서식은 **충청북도교육청 기준**입니다.
> - **다른 시·도 교육청 서식은 추후 도입 예정**입니다. (교육청마다 서식이 달라 셀 주소·체크박스 매핑을 새로 맞춰야 합니다.)

---

## 무엇을 하나

다음 3종 서류를 실제 사안 내용으로 채워 생성합니다.

1. **학교폭력 사안접수 보고서**
2. **학교폭력 전담기구 심의결과 보고서**
3. **학교장 자체해결·종결 결과 보고서(통합)**

### 두 가지 흐름
- **흐름 ① — 사안접수**: 사안 정황을 입력하면 사안접수 보고서를 생성.
- **흐름 ② — 사안조사 이후 분기**: 사안조사 보고서를 제시하면, 간단한 확인을 거쳐 분기별 서류를 생성.
  - **자체해결** (4요건 충족 + 피해측 동의) → 전담기구 보고 + 자체해결 결과 보고 + **자체해결 동의서**(피해측 서명)
  - **종결** (학교폭력 아님·오인신고 등) → 전담기구 보고 + 종결 결과 보고 + **종결 동의서**(피해측 서명)
  - **심의위 이송** (요건 미충족 또는 동의 미제출) → 전담기구 보고

### 핵심 원칙
- **빈칸 원칙**: 모르거나 불확실한 값은 추측하지 않고 빈칸으로 둔다(한글에서 직접 채움). 법적 분류(피해유형·자체해결 요건 등)는 지시가 있을 때만 채운다.
- **생성 전 1회 확인**: 곧바로 만들지 않고 핵심 항목(접수일시·신고자·피해유형·즉시분리 여부)을 한 번에 모아 확인한 뒤 생성.
- **행정문체·분량**: 자유서술 칸(사안 내용)은 최소 500자 이상, 명사형 종결어미(~음/~함)로 작성. 사실을 지어내지 않고 육하원칙으로 상술하되, 분량이 부족하면 부족한 사실관계를 추가로 확인해 보강.
- **동의서는 완곡하게**: 피해 학생·보호자가 읽고 서명하는 자체해결/종결 동의서의 사안 내용은 사실을 따르되 **완곡·객관적 표현으로 500자 내외**(자극적 묘사 금지, 2차 가해 방지).
- **글자 겹침 방지·관련학생 행 자동 복제** 등 한글 양식 채움의 까다로운 부분을 자동 처리.

---

## 요구사항

| 의존성 | 용도 | 비고 |
|---|---|---|
| **kordoc MCP** | 문서 파싱·검증 (`parse_document` 등) | 한국 문서(HWP/HWPX) 처리 |
| **Python lxml** | 표·체크박스 채움 | `pip install lxml` |

---

## 설치 및 사용

먼저 저장소를 받습니다.

```bash
git clone https://github.com/Nampard/school-violence-docs.git
```

### 1) Claude Code (CLI · 데스크톱 앱)

스킬 디렉토리를 개인 스킬 폴더에 복사하면 됩니다.

```bash
cp -r school-violence-docs/skills/school-violence-docs ~/.claude/skills/
# 또는 패키지로:  unzip school-violence-docs/school-violence-docs.skill -d ~/.claude/skills/
```

설치 후 대화창에 **"학폭 사안접수서 만들어줘"**, **"이 조사보고서로 자체해결 서류 뽑아줘"** 처럼 요청하면 스킬이 자동으로 트리거됩니다. (kordoc MCP·lxml 사전 점검 후 진행)

### 2) Cowork

Cowork도 동일한 Agent Skills 형식을 지원합니다. `skills/school-violence-docs/` 폴더(또는 `.skill` 패키지)를 Cowork의 스킬로 추가하고, **kordoc MCP를 연결**하고 **lxml이 설치**돼 있으면 Claude Code와 동일하게 자동 트리거됩니다. 자연어로 사안을 설명하면 같은 흐름으로 문서를 생성합니다.

### 3) Codex · 일반 터미널

Codex는 `.skill` 자동 트리거를 지원하지 않습니다. 대신 **`skills/school-violence-docs/README.md`(직접 실행 가이드)** 를 읽히고 스크립트를 직접 호출하면 동일하게 동작합니다(채움 엔진은 순수 Python이라 Claude 의존성이 없습니다).

```bash
cd school-violence-docs/skills/school-violence-docs/scripts
python3 fill_jeopsu.py      ../assets/templates/사안접수_빈양식.hwpx       data.json  out.hwpx
python3 fill_jeondamgigu.py ../assets/templates/전담기구심의_빈양식.hwpx   data.json  out.hwpx
python3 fill_result.py      ../assets/templates/자체해결종결_빈양식.hwpx   data.json  out.hwpx
```

`data.json` 스키마·예시는 [skills/school-violence-docs/README.md](skills/school-violence-docs/README.md)를 참고하세요.

---

## 디렉토리 구조

```
school-violence-docs/
├── README.md                       ← (이 파일) 프로젝트 소개
├── LICENSE                         ← MIT
├── school-violence-docs.skill      ← 배포용 패키지(zip)
├── 학교폭력_행정서류_작성규약.md      ← 전체 작성 규약(원칙·분기·문체)
└── skills/school-violence-docs/
    ├── SKILL.md                    ← 스킬 본문(자동 트리거 규약)
    ├── README.md                   ← 직접 실행 가이드(Codex·터미널)
    ├── scripts/                    ← 채움 엔진(Python, lxml)
    ├── assets/templates/           ← 빈 양식 hwpx 3종(충북교육청 기준)
    └── references/                 ← 필드·셀 매핑, 업무흐름
```

> 개인정보 보호: 실제 사안 파일·생성물은 저장소에 포함되지 않습니다. 양식과 코드에는 실명·연락처가 없습니다.

---

## 라이선스

[MIT License](LICENSE) — 누구나 자유롭게 사용·수정·재배포할 수 있습니다.
