# -*- coding: utf-8 -*-
"""학교폭력 공문(기안문 본문) 채우기 — 붙임 서류를 보내는 '껍데기' 공문 6종.
사용법: python fill_gongmun.py <공문_빈양식.hwpx> <data.json> <출력.hwpx>
      → hwpx 파일을 저장하고, 동시에 NEIS 복붙용 텍스트를 표준출력에 찍는다.

빈 양식은 6쪽(공문 6종)이 한 파일에 들어 있다. `종류`로 고른 쪽만 남기고 나머지 쪽은 지운 뒤 채운다.

종류 6종과 분기:
  접수          #1 학교폭력 사안접수 보고            [흐름① 접수]      교육지원청 발송
  개최          #2 제1회 전담기구 심의 개최          [흐름② 사전]      내부결재
  결과          #3 제1회 전담기구 심의 결과 보고      [흐름② 사후]      내부결재
  자체해결내부   #4 자체해결(종결) 결과 보고 [내부결재] [자체해결·종결]   내부결재
  자체해결청     #5 자체해결 결과 보고 [교육지원청]    [자체해결·종결]   교육지원청 발송
  심의위        #6 심의위원회 개최 요청              [심의위 이송]     교육지원청 발송

data.json (모르는 값은 생략 → 양식의 플레이스홀더가 그대로 남아 한글에서 채울 수 있음):
{
  "종류": "접수",
  "사안번호": "6", "사안연도": "2026",
  "학교약칭": "○○고",              # 사안번호에 쓰임(○○고-2026-6호)
  "교육지원청": "○○",               # 종류=심의위. '○○교육지원청'으로 들어감
  "관련기안": [                      # 선행 공문의 기안번호. 본문 '관련' 항목에 순서대로 채움
    "○○고등학교-1234(2026.6.12.)",   # 부족하면 남은 자리는 플레이스홀더 유지(빈칸 원칙)
    "○○고등학교-1240(2026.6.30.)"
  ],
  "일시": "2026.6.30.(화) 14:30",    # 종류=개최
  "장소": "본교 1층 회의실",
  "위원": "교감 000, 책임교사 000, 보건교사 000, 상담교사 000, 학부모위원 000",
  "학생": [                          # 종류=심의위 (표). 3명 초과 시 행 자동 복제
    {"구분": "피해관련 학생", "소속학교": "○○고등학교", "학년반": "1-3",
     "이름": "홍길동", "생년월일": "2010.00.00.", "사안번호": "○○고 2026-6", "학생선수": ""}
  ]
}
※ 붙임 목록은 양식 그대로 둔다. 심의위(#6) 붙임 10종에는 '※ 해당 경우만' 조건부 항목이 많아
  임의로 지우면 누락 위험이 있다 — 담당자가 해당 없는 항목을 한글에서 지우는 편이 안전하다.
"""
import sys, json, re
import hwpx_lib as H

KIND_PAGE = {"접수": 0, "개최": 1, "결과": 2, "자체해결내부": 3, "자체해결청": 4, "심의위": 5}

# 관련 기안번호: '○○○○학교-0000(20○○.00.00.)' / '0000학교-0000(...)' / '○○○○중-00000 (...)호'
RE_GIAN = re.compile(r"[◯○0]{2,5}\s*(?:고등학교|중학교|초등학교|학교|고|중|초)\s*-\s*0{4,5}\s*\([^)]*\)(?:\s*호)?")
# 사안번호: '◯◯고-20○○-1호' / '○○초-20○○-○○호' / '00중-2026-00호' / '○○중 2026-1'
RE_SANO = re.compile(r"[◯○0]{2,4}\s*(?:고등학교|중학교|초등학교|고|중|초)\s*[-\s]\s*20[○\d]{2}\s*-\s*[○\d]{1,2}\s*호?")
RE_GIAN_HINT = re.compile(r"\(사안\s*번호\s*기입\)")
RE_CHEONG = re.compile(r"[◯○]{2,4}교육지원청")


def page_ranges(tops):
    """pageBreak=1을 경계로 최상위 문단을 쪽별 (start, end) 구간으로 나눈다."""
    starts = [0] + [i for i, p in enumerate(tops) if i > 0 and p.get("pageBreak") == "1"]
    return [(s, starts[k + 1] if k + 1 < len(starts) else len(tops)) for k, s in enumerate(starts)]


def main(template, data_path, out_path):
    d = json.load(open(data_path, encoding="utf-8"))
    kind = d.get("종류", "접수")
    if kind not in KIND_PAGE:
        raise SystemExit(f"종류는 {list(KIND_PAGE)} 중 하나여야 함 (받은 값: {kind!r})")

    workdir, sec, tree, root = H.load(template)
    tops = H.top_paragraphs(root)
    ranges = page_ranges(tops)
    if len(ranges) != 6:
        print(f"⚠️ 양식 쪽수가 6이 아님({len(ranges)}) — 템플릿이 바뀌었는지 확인 필요")
    start, end = ranges[KIND_PAGE[kind]]

    # 고른 쪽 외의 문단은 모두 제거(표는 문단 안에 있어 함께 사라짐)
    for i, p in enumerate(tops):
        if not (start <= i < end):
            p.getparent().remove(p)
    keep = tops[start:end]
    keep[0].set("pageBreak", "0")   # 앞에 빈 쪽이 생기지 않도록

    # 사안번호 문자열
    sano = ""
    if d.get("사안번호"):
        sano = f"{d.get('학교약칭', 'OO고')}-{d.get('사안연도', '2026')}-{d['사안번호']}호"

    gian_left = list(d.get("관련기안", []))
    year = str(d.get("사안연도", "")) if d.get("사안번호") else ""

    for p in keep:
        txt = new = H.para_text(p)
        # 관련 기안번호(더 구체적이라 먼저). 사용자가 준 만큼만 채우고, 모자란 자리는 원본 유지(빈칸 원칙).
        # 안 채운 자리는 토큰으로 감춰 둔다 — 그 안의 '20○○.00.00.'까지 연도 치환되면 곤란하다.
        kept = []

        def sub_gian(m):
            if gian_left:
                return gian_left.pop(0)
            kept.append(m.group())
            return f"\x00{len(kept) - 1}\x00"

        new = RE_GIAN.sub(sub_gian, new)
        if year:                                               # 본문의 '20○○. 학교폭력(...)' 연도
            new = re.sub(r"20[○◯]{2}", year, new)
        for i, ph in enumerate(kept):
            new = new.replace(f"\x00{i}\x00", ph)
        if sano:
            new = RE_SANO.sub(sano, new)
            new = RE_GIAN_HINT.sub(f"({sano})", new)
        if d.get("교육지원청"):
            new = RE_CHEONG.sub(f"{d['교육지원청']}교육지원청", new)
        if kind == "개최":                                      # 일시·장소·대상 줄 교체
            if d.get("일시"):
                new = re.sub(r"(가\.\s*일시:\s*).*", lambda m: m.group(1) + d["일시"], new)
            if d.get("장소"):
                new = re.sub(r"(나\.\s*장소:\s*).*", lambda m: m.group(1) + d["장소"], new)
            if d.get("위원"):
                new = re.sub(r"(다\.\s*대상:\s*본교 전담기구 위원)\(.*?\)",
                             lambda m: m.group(1) + f"({d['위원']})", new)
        if new != txt:
            H.set_para_text(p, new)

    # 심의위 요청서의 관련학생 표.
    # 이 표에는 양식 예시(○○중학교 3-1 …)가 박혀 있어, 채우기 전에 반드시 비운다.
    # 학생을 안 주면 빈 표로 남겨 담당자가 한글에서 채우게 한다(예시가 그대로 제출되는 사고 방지).
    if kind == "심의위":
        tbls = H.tables(root)
        if tbls:
            t = tbls[0]
            students = d.get("학생", [])
            data_rows = t.findall(H.q("tr"))[1:]                # 0행은 머리글
            if students and len(students) > len(data_rows):     # 인원이 많으면 행 복제
                H.clone_block_after(t, [data_rows[-1]], data_rows[-1], len(students) - len(data_rows))
                data_rows = t.findall(H.q("tr"))[1:]
            elif students and len(students) < len(data_rows):   # 남는 예시 행은 삭제
                for tr in data_rows[len(students):]:
                    t.remove(tr)
                H.renumber_rows(t)
                data_rows = t.findall(H.q("tr"))[1:]
            cols = ["구분", "소속학교", "학년반", "이름", "생년월일", "사안번호", "학생선수"]
            for i, tr in enumerate(data_rows):
                st = students[i] if i < len(students) else {}
                tcs = tr.findall(H.q("tc"))
                for ci, key in enumerate(cols):
                    if ci < len(tcs):
                        H.clear_cell(tcs[ci])                   # 양식 예시 제거 후
                        H.set_cell(tcs[ci], st.get(key, ""))    # 값이 있으면 채움

    body = H.replace_text(tree, []).decode("utf-8")
    body = H.apply_school(body, d)
    body = H.reflow_paragraphs(body)     # 캐시된 줄 레이아웃 제거 → 글자 겹침 방지
    H.write_section(sec, body.encode("utf-8"))
    H.save(workdir, template, out_path)

    # NEIS 복붙용 텍스트 (기안창에 그대로 붙여넣기)
    print("=" * 60)
    print(f"[NEIS 복붙용] {kind}")
    print("=" * 60)
    for p in keep:
        line = H.para_text(p).rstrip()
        if line.strip():
            print(line)
        tb = p.find(f".//{H.q('tbl')}")     # 표는 문단 텍스트에 안 잡히므로 따로 그려 준다
        if tb is not None:
            for tr in tb.findall(H.q("tr")):
                cells = [re.sub(r"\s+", " ", "".join(tc.itertext())).strip()
                         for tc in tr.findall(H.q("tc"))]
                print("| " + " | ".join(cells) + " |")
    print("=" * 60)
    print("saved", out_path)
    if gian_left:
        print(f"⚠️ 관련기안 {len(gian_left)}건이 쓰이지 않음 — 이 공문의 '관련' 항목 수보다 많이 준 것")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
