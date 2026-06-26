# -*- coding: utf-8 -*-
"""학교장 자체해결/종결 동의서 채우기 — 피해관련 학생·보호자가 읽고 서명하는 문서.
사용법: python fill_donguiseo.py <빈양식.hwpx> <data.json> <출력.hwpx>

채움 방식: 사안번호·관련학생 그리드·사안내용 모두 lxml(set_cell, 바이트 정확)로 채운다.
  - kordoc fill_form은 라벨 "사안 조사 내용" 칸은 잡지만 ① 관련학생 그리드·사안번호는 못 잡고(신뢰도 0.33)
    ② 일부 한글(예 "다툼이"→"다투이")을 손상시키는 것이 확인됨. 피해측이 서명하는 공식 문서라 글자 손상은
    허용되지 않으므로, 다른 3종 보고서와 동일하게 lxml로 채운다(서식 100% 보존 + 글자 그대로).

※ 동의서 '사안 내용'은 사안조사 보고서의 사실을 따르되, 피해측이 읽고 서명하는 점을 고려해
  **자극적이지 않은 완곡한 표현으로 500자 내외**로 작성한다(보고서의 '최소 500자'와 다름).

data.json (모르는 값은 생략/"" → 빈칸):
{
  "종류": "자체해결",                 # "자체해결"(피해학생 2칸) | "종결"(3칸)
  "사안번호": "5", "사안연도": "2026",  # 사안연도 미지정 시 양식 기본 유지
  "학교명": "충주공업고등학교", "학교약칭": "충주공고",  # 없으면 OO고 플레이스홀더 유지
  "사안내용": "",                     # (선택) 완곡 500자 내외. fill_form으로 채웠으면 생략
  "학생": [                           # 피해관련 학생(개인별 작성이 원칙)
    {"소속학교": "충주공업고등학교", "학년반": "1-3", "성명": "홍길동"}
  ]
}
"""
import sys, json, re
import hwpx_lib as H

# 종류별: 학생 데이터행(rowAddr), 사안내용 셀(row,col)
CFG = {
    "자체해결": {"rows": [2, 4],    "내용": (5, 1)},
    "종결":   {"rows": [2, 4, 6], "내용": (7, 1)},
}

def main(template, data_path, out_path):
    d = json.load(open(data_path, encoding="utf-8"))
    cfg = CFG[d.get("종류", "자체해결")]
    workdir, sec, tree, root = H.load(template)
    t = H.tables(root)[1]

    # 관련학생 그리드: 행 r, 열 1/2/3 = 소속학교 / 학년·반 / 학생성명
    for r, st in zip(cfg["rows"], d.get("학생", [])):
        for col, key in ((1, "소속학교"), (2, "학년반"), (3, "성명")):
            c = H.cell_by_addr(t, r, col)
            if c is not None:
                H.set_cell(c, st.get(key, ""))

    # 사안 내용(선택) — fill_form을 안 썼을 때만. 완곡 500자 내외 권장.
    if d.get("사안내용"):
        rr, cc = cfg["내용"]
        c = H.cell_by_addr(t, rr, cc)
        if c is not None:
            H.set_cell(c, d["사안내용"])
        if len(d["사안내용"]) > 650:
            print(f"⚠️ 동의서 '사안내용'이 {len(d['사안내용'])}자 — 피해측이 서명하는 문서이니 완곡·간결히 500자 내외 권장")

    # 사안번호: 셀 (0,0)의 연도-번호 자리( -2026-OO / -20○○-○○ )를 치환. 학교약칭은 apply_school이 처리.
    # '사안번호' 글자와 연도 자리가 서로 다른 run에 나뉘어 있을 수 있어, 셀 안 모든 t 노드를 훑어 패턴이 든 곳을 바꾼다.
    if d.get("사안번호"):
        yr = str(d.get("사안연도", "2026"))
        c0 = H.cell_by_addr(t, 0, 0)
        pat = re.compile(r"-20[\d○]{2}-[O○]{2}")
        for tn in (c0.findall(f".//{H.q('t')}") if c0 is not None else []):
            if tn.text and pat.search(tn.text):
                tn.text = pat.sub(f"-{yr}-{d['사안번호']}", tn.text)

    body = H.replace_text(tree, []).decode("utf-8")
    body = H.apply_school(body, d)
    body = H.reflow_paragraphs(body)   # 캐시된 줄 레이아웃 제거 → 글자 겹침 방지
    H.write_section(sec, body.encode("utf-8"))
    H.save(workdir, template, out_path)
    print("saved", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
