# -*- coding: utf-8 -*-
"""
학교장 자체해결·종결 결과 보고서(통합) 채우기.
사용법: python fill_result.py <빈양식.hwpx> <data.json> <출력.hwpx>

data.json:
{
  "사안번호": "5",
  "학교명": "○○고등학교", "학교약칭": "○○고",   # (선택) 없으면 'OO고등학교'/'OO고' 유지
  "mode": "자체해결",                # "자체해결" | "종결"
  "학생": [
    {"학교": "○○고등학교", "학년반번호": "1508", "성명": "이민수", "보호자": ""},
    ...
  ],
  "사안조사내용": "...",
  "관계회복": "미운영",
  "오인신고항목": 1                  # mode=종결일 때만: 1|2|3 (학폭아님 종결 사유 항목)
}
분기: 자체해결이면 '학교폭력 자체해결 사안 (O)', 종결이면 '학교폭력이 아닌 사안 종결 (O)'+해당 항목 O.
※ 학생이 5명 이상이면 학생 블록(헤더+데이터)을 자동 복제해 전원 채움(하위 고정행은 자동 이동).
"""
import sys, json
import hwpx_lib as H

def main(template, data_path, out_path):
    d = json.load(open(data_path, encoding="utf-8"))
    workdir, sec, tree, root = H.load(template)
    t = H.tables(root)[0]
    rows = t.findall(H.q('tr'))

    # 학생 1명 = 2행 묶음(헤더+데이터). 기본 4명(블록 0~3 = tr 0/1, 2/3, 4/5, 6/7).
    # 4명 초과 시 마지막 블록(rows[6],rows[7])을 복제해 표를 늘린다 → 하위 고정행은 off만큼 밀린다.
    students = d.get("학생", [])
    extra = max(0, len(students) - 4)
    if extra:
        H.clone_block_after(t, [rows[6], rows[7]], rows[7], extra)
        rows = t.findall(H.q('tr'))
    off = 2 * extra

    # 학생 데이터행 = 1,3,5,7,(9,11,…) (각 tc[0..3]=소속학교/학년반번호/학생이름/보호자이름)
    for i, st in enumerate(students):
        dr = rows[1 + i * 2].findall(H.q('tc'))
        H.set_cell(dr[0], st.get("학교", ""))
        H.set_cell(dr[1], st.get("학년반번호", ""))
        H.set_cell(dr[2], st.get("성명", ""))
        H.set_cell(dr[3], st.get("보호자", ""))

    if d.get("사안조사내용"):
        H.set_cell(rows[8 + off].findall(H.q('tc'))[1], d["사안조사내용"])

    mode = d.get("mode", "자체해결")
    if mode == "자체해결":
        H.check_paren(rows[13 + off].findall(H.q('tc'))[0])
        H.set_cell(rows[13 + off].findall(H.q('tc'))[1], "O — 자체해결 요건 충족 및 피해측 동의")
    else:  # 종결(학폭 아님)
        H.check_paren(rows[9 + off].findall(H.q('tc'))[1])
        item = int(d.get("오인신고항목", 1))   # 항목1→row10, 2→row11, 3→row12
        H.set_cell(rows[9 + off + item].findall(H.q('tc'))[1], "O")

    if d.get("관계회복"):
        H.set_cell(rows[15 + off].findall(H.q('tc'))[1], d["관계회복"])

    repls = []
    if d.get("사안번호"):
        yr = str(d.get("사안연도", "2026"))   # 사안번호 연도(기본 2026). 작년 이월 사안 등은 "2025" 지정
        repls.append(("-2026-  호", f"-{yr}-{d['사안번호']}호"))
    # 분량 안전망: '사안조사내용'은 최소 500자 권장
    if d.get("사안조사내용") and len(d["사안조사내용"]) < 500:
        print(f"⚠️ '사안조사내용'이 {len(d['사안조사내용'])}자로 500자 미만 — 사실관계를 더 확인해 보강 권장")

    body = H.replace_text(tree, repls).decode("utf-8")
    body = H.apply_school(body, d)
    body = H.reflow_paragraphs(body)   # 캐시된 줄 레이아웃 제거 → 글자 겹침 방지
    H.write_section(sec, body.encode("utf-8"))
    H.save(workdir, template, out_path)
    print("saved", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
