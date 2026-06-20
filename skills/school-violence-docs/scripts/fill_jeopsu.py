# -*- coding: utf-8 -*-
"""
사안접수 보고서 채우기.
사용법: python fill_jeopsu.py <빈양식.hwpx> <data.json> <출력.hwpx>

data.json (모르는 값은 키 생략 또는 "" → 빈칸 유지):
{
  "사안번호": "6",                      # ○○고-2026-<N>호 의 N만
  "접수일시": "2026년 12월 오전 ...",
  "신고자": "2학년 3반 담임교사",        # 신고자(성명,신분)
  "접수경로": "담임 상담 중 인지·신고",
  "관련학교명": "해당없음 (같은 학교)",
  "학교명": "○○고등학교",            # (선택) 정식 교명. 없으면 'OO고등학교' 유지
  "학교약칭": "○○고",                 # (선택) 사안번호용 약칭. 없으면 'OO고' 유지
  "교감": "", "교감전화": "",         # (선택) 학교 고유 교직원 — 없으면 빈칸
  "담당자": "", "담당전화": "", "접수자": "",  # (선택) 예 "홍길동(학교폭력담당교사)"
  "가해학생2호조치": "미시행",         # (선택) 제2호(접촉·협박·보복 금지) 긴급조치 시행 여부.
                                      #        예 "2026.6.12. 시행" / "미시행". 없으면 빈칸
  "사실확인": {"관련학생": "...", "일시": "...", "장소": "", "내용": "...",
              "유형": "기타(성희롱)"},   # 유형: 체크할 항목 키워드. '성폭력' 등은 신중히(법적효과)
  "학생": [
    {"학교": "○○고등학교", "학번": "2-3", "성명": "홍길동", "성별": "남",
     "비고": ["가해관련"]},
    {"학교": "○○고등학교", "학번": "2-3", "성명": "김철수", "성별": "",
     "비고": ["피해관련", "특수교육대상자", "다문화학생"]}
  ]
}
유형 키워드→체크박스 매핑은 references/field-maps.md 참조.
※ 학생이 5명 이상이면 양식 학생행을 자동 복제해 전원 채움(별지 불필요).
"""
import sys, json
import hwpx_lib as H

TYPE_BOX = {  # 유형 입력 키워드 → 양식의 □유형 라벨
    "폭행": "□폭행", "신체폭력": "□폭행", "언어폭력": "□언어폭력", "따돌림": "□따돌림",
    "강요": "□강요", "사이버폭력": "□사이버폭력", "금품갈취": "□금품갈취",
    "기타": "□기타", "성희롱": "□기타", "아동학대": "□아동학대", "성폭력": "□성폭력",
}

def main(template, data_path, out_path):
    d = json.load(open(data_path, encoding="utf-8"))
    workdir, sec, tree, root = H.load(template)
    tbls = H.tables(root)
    main_t, nested = tbls[1], tbls[2]   # [0]제목 [1]본문 [2]사실확인 중첩표

    # 단순 셀 (cellAddr)
    if d.get("접수일시"): H.set_cell(H.cell_by_addr(main_t, 3, 1), d["접수일시"])
    if d.get("신고자"):   H.set_cell(H.cell_by_addr(main_t, 4, 1), d["신고자"])
    if d.get("접수경로"): H.set_cell(H.cell_by_addr(main_t, 4, 11), d["접수경로"])
    if d.get("관련학교명"):
        c = H.cell_by_addr(main_t, 18, 3)
        if c is not None: H.set_cell(c, d["관련학교명"])

    # 학교 고유 헤더(교직원 등) — 주면 채우고, 없으면 빈칸 유지 (학교명은 아래 apply_school에서 처리)
    if d.get("교감"):     H.set_cell(H.cell_by_addr(main_t, 1, 8), d["교감"])
    if d.get("교감전화"): H.set_cell(H.cell_by_addr(main_t, 2, 8), d["교감전화"])
    if d.get("담당자"):   H.set_cell(H.cell_by_addr(main_t, 1, 14), d["담당자"])
    if d.get("담당전화"): H.set_cell(H.cell_by_addr(main_t, 2, 14), d["담당전화"])
    if d.get("접수자"):   H.set_cell(H.cell_by_addr(main_t, 5, 1), d["접수자"])
    # 가해학생 제2호 조치(접촉·협박·보복 금지 긴급조치) 시행 여부 — 자유기입, 없으면 빈칸
    if d.get("가해학생2호조치"): H.set_cell(H.cell_by_addr(main_t, 7, 1), d["가해학생2호조치"])

    # 관련학생 그리드 (가해관련+탈북학생 포함 tr = 학생행). 위치순 tc[0..5]
    def find_srows():
        return [tr for tr in main_t.findall(H.q('tr'))
                if "가해관련" in "".join(tr.itertext()) and "탈북학생" in "".join(tr.itertext())]
    srows = find_srows()
    students = d.get("학생", [])
    # 학생이 양식 칸(기본 4명)을 넘으면 마지막 학생행을 복제해 표를 늘린다(전원 한 문서에 정식 서식으로).
    if srows and len(students) > len(srows):
        added = len(students) - len(srows)
        H.clone_block_after(main_t, [srows[-1]], srows[-1], added)
        # '관련학생' 세로병합 라벨이 새 행까지 덮도록 rowSpan 확장(안 하면 새 행 앞에 빈 칸 발생)
        H.extend_rowspan_label(main_t, "관련학생", added)
        srows = find_srows()
    for tr, st in zip(srows, students):
        tcs = tr.findall(H.q('tc'))
        H.set_cell(tcs[0], st.get("학교", ""))
        H.set_cell(tcs[1], st.get("학번", ""))
        H.set_cell(tcs[2], st.get("성명", ""))
        H.set_cell(tcs[3], st.get("성별", ""))
        for lab in st.get("비고", []):
            H.check_box(tcs[5], lab)

    # 사실확인 중첩표: 행 0관련학생 1일시 2장소 3내용 4유형, 값=tc[1]
    sc = d.get("사실확인", {})
    nrows = nested.findall(H.q('tr'))
    keymap = {0: "관련학생", 1: "일시", 2: "장소", 3: "내용"}
    for i, key in keymap.items():
        if sc.get(key):
            H.set_cell(nrows[i].findall(H.q('tc'))[1], sc[key])
    # 유형 체크
    if sc.get("유형"):
        box = TYPE_BOX.get(sc["유형"].split("(")[0].strip())
        suffix = ""
        if "(" in sc["유형"]:  # 예: '기타(성희롱)' → ■기타(성희롱)
            suffix = sc["유형"][sc["유형"].index("("):]
        if box:
            for r in H.runs_of(nrows[4].findall(H.q('tc'))[1]):
                t = r.find(H.q("t"))
                if t is not None and t.text and box in t.text:
                    t.text = t.text.replace(box, "■" + box[1:] + suffix, 1)
                    break

    # 사안번호 + 학교명/약칭 (직렬화 후 치환)
    repls = []
    if d.get("사안번호"):
        repls.append(("* 사안번호: OO고-2026-", f"* 사안번호: OO고-2026-{d['사안번호']}호"))
    body = H.replace_text(tree, repls).decode("utf-8")
    body = H.apply_school(body, d)
    body = H.reflow_paragraphs(body)   # 캐시된 줄 레이아웃 제거 → 글자 겹침 방지
    H.write_section(sec, body.encode("utf-8"))
    H.save(workdir, template, out_path)
    print("saved", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
