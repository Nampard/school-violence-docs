# -*- coding: utf-8 -*-
"""
전담기구 심의결과 보고서 채우기 (자유서술형 + 4요건 O/X 표).
사용법: python fill_jeondamgigu.py <빈양식.hwpx> <data.json> <출력.hwpx>

data.json (모르는 값은 생략/"" → 빈칸):
{
  "사안번호": "5",
  "학교명": "○○고등학교", "학교약칭": "○○고",   # (선택) 없으면 'OO고등학교'/'OO고' 유지
  "일시": "2026년 6월 15일 (월요일) 13:00",
  "참석자": "교감, 학생생활안전부장, 학부모위원 3명",
  "조사내용": "본 사안은 ... 자체해결 4요건 충족함.",
  "요건": ["O","O","O","O"],          # 1~4 해당여부. 모르면 [] 또는 "" 항목
  "동의": "O (자체해결 동의)",          # 동의서 제출 여부
  "결정": "... 학교장 자체해결로 결정함."
}
※ 공동학폭이면 전담기구는 각 학교가 각자 운영 → 자교 기준(일시·참석자)으로 작성.
"""
import sys, json
import hwpx_lib as H

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main(template, data_path, out_path):
    d = json.load(open(data_path, encoding="utf-8"))
    workdir, sec, tree, root = H.load(template)
    tbls = H.tables(root)
    t1 = tbls[1]   # 4요건 표
    rows = t1.findall(H.q('tr'))
    yogeon_cells = [rows[1].findall(H.q('tc'))[2], rows[2].findall(H.q('tc'))[1],
                    rows[3].findall(H.q('tc'))[1], rows[4].findall(H.q('tc'))[1]]
    for cell, val in zip(yogeon_cells, d.get("요건", [])):
        if val:
            H.set_cell(cell, val)
    if d.get("동의"):
        H.set_cell(rows[6].findall(H.q('tc'))[1], d["동의"])

    repls = []
    if d.get("사안번호"):
        yr = str(d.get("사안연도", "2026"))   # 사안번호 연도(기본 2026). 작년 이월 사안 등은 "2025" 지정
        repls.append(("2026- 호", f"{yr}-{d['사안번호']}호"))
        repls.append(("2026-0  호", f"{yr}-{int(d['사안번호']):02d}호"))
    if d.get("일시"):
        repls.append(("2026년   월   일 (  요일)", esc(d["일시"])))
    if d.get("참석자"):
        repls.append(("3. 참 석 자 : ", f"3. 참 석 자 : {esc(d['참석자'])}  "))
    if d.get("조사내용"):
        repls.append(("<hp:t>  • </hp:t>", f"<hp:t>  • {esc(d['조사내용'])}</hp:t>"))
    if d.get("결정"):
        repls.append(("<hp:t> • </hp:t>", f"<hp:t> • {esc(d['결정'])}</hp:t>"))

    body = H.replace_text(tree, repls).decode("utf-8")
    body = H.apply_school(body, d)
    body = H.reflow_paragraphs(body)   # 캐시된 줄 레이아웃 제거 → 글자 겹침 방지
    H.write_section(sec, body.encode("utf-8"))
    H.save(workdir, template, out_path)
    print("saved", out_path)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
