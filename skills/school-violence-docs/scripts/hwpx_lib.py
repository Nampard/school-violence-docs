# -*- coding: utf-8 -*-
"""
hwpx_lib — 한글 hwpx 서식의 표 셀·체크박스를 셀 주소 기반으로 안전하게 채우는 코어 라이브러리.

왜 이렇게 하나:
- kordoc의 fill_form은 단순 라벨-값 행만 안정적으로 채운다. 표 그리드·중첩표·체크박스는
  fill_form이 골격을 덮어쓰거나 못 건드린다. 그래서 그런 칸은 hwpx 내부 XML(OWPML)을
  lxml로 직접 편집한다. lxml은 prefix와 바이트를 보존하며 왕복(round-trip)해 한글이 깨지지 않는다.
- hwpx는 zip이며 mimetype이 맨 앞·무압축(STORED)이어야 한글이 연다. save()가 이를 보장한다.
"""
from lxml import etree
import zipfile, os, shutil, tempfile, re, copy

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
def q(tag): return f"{{{HP}}}{tag}"
DECL = b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'


def load(template_path):
    """템플릿 hwpx를 임시 폴더에 풀고 (workdir, section0_path, tree, root) 반환."""
    workdir = tempfile.mkdtemp(prefix="hwpx_")
    with zipfile.ZipFile(template_path) as z:
        z.extractall(workdir)
    sec = os.path.join(workdir, "Contents", "section0.xml")
    tree = etree.parse(sec)
    return workdir, sec, tree, tree.getroot()


def tables(root):
    return root.findall(f".//{q('tbl')}")


def first_run(tc):
    return tc.find(f"{q('subList')}/{q('p')}/{q('run')}")


def runs_of(tc):
    return tc.findall(f"{q('subList')}/{q('p')}/{q('run')}")


def set_cell(tc, text):
    """셀의 첫 문단 run에 텍스트를 넣는다(빈 값 셀 채움). text가 빈 문자열/None이면 건드리지 않음(빈칸 유지)."""
    if text is None or text == "":
        return False
    run = first_run(tc)
    for t in run.findall(q("t")):
        run.remove(t)
    et = etree.SubElement(run, q("t"))
    et.text = text
    return True


def clear_cell(tc):
    """셀을 강제로 비운다. set_cell은 빈 값이면 건드리지 않으므로(빈칸 원칙), 양식에 박힌
    예시 데이터를 지워야 할 때 쓴다. 예시가 남은 채 제출되는 사고를 막는 용도."""
    run = first_run(tc)
    if run is None:
        return False
    for t in run.findall(q("t")):
        run.remove(t)
    etree.SubElement(run, q("t")).text = ""
    return True


def check_box(tc, label):
    """셀 안에서 label run 다음의 '□'를 '■'로 1회 바꾼다(예: '가해관련' → 다음 칸의 □→■)."""
    rs = runs_of(tc)
    for i, r in enumerate(rs):
        t = r.find(q("t"))
        if t is not None and (t.text or "").strip() == label:
            for j in range(i + 1, min(i + 3, len(rs))):
                t2 = rs[j].find(q("t"))
                if t2 is not None and t2.text and "□" in t2.text:
                    t2.text = t2.text.replace("□", "■", 1)
                    return True
    return False


def check_paren(tc):
    """셀 안의 '( )'(괄호 안 공백만)를 '( O )'로 1회 바꾼다(분기 체크 표시)."""
    for r in runs_of(tc):
        t = r.find(q("t"))
        if t is not None and t.text and re.search(r"\(\s+\)", t.text):
            t.text = re.sub(r"\(\s+\)", "( O )", t.text, count=1)
            return True
    return False


def renumber_rows(table):
    """표의 모든 tc.cellAddr.rowAddr를 자신이 속한 tr의 순번으로 다시 매기고 rowCnt를 갱신한다.
    행을 추가/삭제한 뒤 호출한다. 이 양식들은 rowAddr == tr 순번이고 rowSpan은 셀 속성으로
    별도 유지되므로(세로 병합) 이 재번호가 안전하다."""
    trs = table.findall(q("tr"))
    for i, tr in enumerate(trs):
        for ca in tr.findall(f"{q('tc')}/{q('cellAddr')}"):
            ca.set("rowAddr", str(i))
    table.set("rowCnt", str(len(trs)))
    return trs


def extend_rowspan_label(table, label_text, delta):
    """table 안에서 텍스트가 label_text이고 세로병합(rowSpan>1)된 라벨 셀의 rowSpan을 delta만큼 늘린다.
    사안접수 '관련학생'처럼 하나의 라벨이 여러 학생 데이터행을 세로로 덮는 경우, 행을 추가하면
    그 병합도 새 행까지 확장해야 빈 칸이 생기지 않는다."""
    for tc in table.findall(f"{q('tr')}/{q('tc')}"):
        span = tc.find(q("cellSpan"))
        if span is None or int(span.get("rowSpan", "1")) <= 1:
            continue
        txt = "".join((t.text or "") for t in tc.findall(f".//{q('t')}")).strip()
        if txt == label_text:
            span.set("rowSpan", str(int(span.get("rowSpan")) + delta))
            return True
    return False


def clone_block_after(table, block_trs, anchor_tr, times):
    """block_trs(연속된 tr 묶음 = 학생 1명분 행)를 times번 복제해 anchor_tr 바로 뒤에 삽입한다.
    복제는 채우기 전(빈 템플릿 상태)에 해야 한다. 삽입 후 renumber_rows로 주소를 정리한다.
    반환: 새로 삽입된 tr들의 평탄 리스트."""
    ref, new_trs = anchor_tr, []
    for _ in range(times):
        for tr in block_trs:
            clone = copy.deepcopy(tr)
            ref.addnext(clone)
            ref = clone
            new_trs.append(clone)
    renumber_rows(table)
    return new_trs


def cell_by_addr(table, row, col):
    """table의 직속 tr/tc 중 cellAddr(rowAddr,colAddr)이 일치하는 셀 반환."""
    for tc in table.findall(f"{q('tr')}/{q('tc')}"):
        ca = tc.find(q("cellAddr"))
        if ca is not None and ca.get("rowAddr") == str(row) and ca.get("colAddr") == str(col):
            return tc
    return None


def replace_text(tree_or_bytes, replacements):
    """직렬화된 XML 문자열에 (old, new) 치환을 1회씩 적용. 자유서술형(전담기구) 칸 채움용.
    replacements: list of (old, new). 반환: bytes."""
    if isinstance(tree_or_bytes, (bytes, bytearray)):
        body = bytes(tree_or_bytes).decode("utf-8")
    else:
        body = etree.tostring(tree_or_bytes, xml_declaration=False, encoding="UTF-8").decode("utf-8")
    for old, new in replacements:
        if old in body:
            body = body.replace(old, new, 1)
    return body.encode("utf-8")


def apply_school(body, d):
    """학교명/학교약칭 플레이스홀더 치환. body는 str. 미제공 시 'OO고등학교'/'OO고' 유지.
    'OO고'가 'OO고등학교'의 접두라, 정식명(긴 것)을 먼저 치환하고 약칭은 '등학교'가 뒤따르지 않을 때만 치환."""
    if d.get("학교명"):
        body = body.replace("OO고등학교", d["학교명"])
        # 종결 동의서의 'OO학교장 귀중'처럼 학교급을 안 박은 범용 표기도 처리한다.
        # 위에서 'OO고등학교'를 먼저 바꿨으므로 여기 남는 건 순수 'OO학교'뿐이다.
        body = body.replace("OO학교", d["학교명"])
    if d.get("학교약칭"):
        body = re.sub(r"OO고(?!등학교)", d["학교약칭"], body)
    return body


def para_text(p):
    """문단(hp:p)의 텍스트를 추출한다. hp:t 안의 <hp:lineBreak/>는 '\\n'으로 바꾼다.

    왜 필요한가: 한 문단이 여러 줄일 때 hwpx는 <hp:t>앞줄<hp:lineBreak/>뒷줄</hp:t> 형태로 담는다.
    이때 lxml의 t.text는 '앞줄'만 주고 '뒷줄'은 lineBreak.tail에 있어, t.text만 읽으면 조용히 누락된다.
    (공문서식의 '가./나.' 관련 기안번호, 붙임 2·3항이 이 형태였다.)

    문단 안에 표(hp:tbl)가 들어 있으면 그 표 안의 글자는 제외한다. 표는 셀 단위로 따로 다뤄야 하고,
    문단 텍스트로 긁어오면 표가 통째로 한 줄처럼 보여 통짜 교체 시 표가 뭉개진다."""
    out = []
    for t in p.findall(f".//{q('t')}"):
        anc, in_tbl = t.getparent(), False
        while anc is not None and anc is not p:
            if anc.tag == q("tbl"):
                in_tbl = True
                break
            anc = anc.getparent()
        if in_tbl:
            continue
        if t.text:
            out.append(t.text)
        for c in t:
            if etree.QName(c).localname == "lineBreak":
                out.append("\n")
            if c.tail:
                out.append(c.tail)
    return "".join(out)


def set_para_text(p, text):
    """문단을 text로 교체한다('\\n'은 <hp:lineBreak/>로 복원). 첫 run만 남기고 거기에 몰아넣는다.

    문단이 여러 run으로 잘게 쪼개진 경우(예: '20|○|○. 학교폭력(...')엔 run 경계를 넘는 치환이
    불가능하므로, 문단 단위로 통째 교체하는 이 방식이 안전하다. 서식은 실질 텍스트를 가진
    run의 것을 이어받는다(첫 run이 들여쓰기 공백뿐인 경우가 있어 그대로 쓰면 서식이 틀어진다).
    표(hp:tbl)를 품은 run은 건드리지 않는다 — 지우면 표가 사라진다."""
    runs = [r for r in p.findall(q("run")) if r.find(f".//{q('tbl')}") is None]
    if not runs:
        return False
    base = next((r for r in runs if "".join(r.itertext()).strip()), runs[0])
    first = runs[0]
    if base is not first and base.get("charPrIDRef"):
        first.set("charPrIDRef", base.get("charPrIDRef"))
    for r in runs[1:]:
        p.remove(r)
    for t in first.findall(q("t")):
        first.remove(t)
    tn = etree.SubElement(first, q("t"))
    parts = text.split("\n")
    tn.text = parts[0]
    for seg in parts[1:]:
        lb = etree.SubElement(tn, q("lineBreak"))
        lb.tail = seg
    return True


def top_paragraphs(root):
    """표(hp:tc) 안에 있지 않은 최상위 문단만 순서대로 반환."""
    return [p for p in root.iter(q("p"))
            if not any(a.tag == q("tc") for a in p.iterancestors())]


def reflow_paragraphs(body):
    """채운 문단의 캐시된 줄 레이아웃(<hp:linesegarray>)을 제거해, 한글이 파일을 열 때 줄 위치를
    스스로 다시 계산(reflow)하게 한다 → '글자 겹침' 해소.

    왜 필요한가: 빈 셀 문단에는 vertpos=0짜리 lineseg가 딱 1개 들어 있다(1줄 기준 캐시).
    set_cell/치환으로 긴 글자를 넣어도 이 캐시는 1줄 그대로라, 자동 줄바꿈된 2번째 줄 이후가
    모두 vertpos=0(같은 높이)에 겹쳐 그려진다. 캐시를 지우면 한글이 칸 너비·폰트에 맞춰
    줄마다 올바른 lineseg를 새로 만든다(칸 너비가 달라도 자동 처리 — 40자 고정 줄바꿈보다 견고).

    텍스트가 있는 문단만 처리한다(빈 문단·라벨도 지워도 무해하나 보수적으로 둠). body는 str(선언 없음).
    한글은 linesegarray가 없으면 렌더 자체가 불가하므로 열 때 반드시 재계산한다."""
    root = etree.fromstring(body.encode("utf-8"))
    for p in root.iter(q("p")):
        txt = "".join(t.text or "" for t in p.findall(f".//{q('t')}"))
        if not txt.strip():
            continue
        lsa = p.find(q("linesegarray"))
        if lsa is not None:
            p.remove(lsa)
    return etree.tostring(root, encoding="UTF-8").decode("utf-8")


def write_section(sec_path, tree_or_bytes):
    """section0.xml을 원본 선언과 함께 기록."""
    if isinstance(tree_or_bytes, (bytes, bytearray)):
        body = bytes(tree_or_bytes)
        if body.lstrip().startswith(b"<?xml"):
            # 선언 포함된 경우 그대로
            open(sec_path, "wb").write(body)
            return
    else:
        body = etree.tostring(tree_or_bytes, xml_declaration=False, encoding="UTF-8")
    open(sec_path, "wb").write(DECL + body)


def save(workdir, template_path, out_path):
    """workdir 내용을 hwpx로 재압축. mimetype은 맨 앞·STORED."""
    names = zipfile.ZipFile(template_path).namelist()
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w") as zout:
        if "mimetype" in names:
            zout.write(os.path.join(workdir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
        for n in names:
            if n == "mimetype":
                continue
            zout.write(os.path.join(workdir, n), n, compress_type=zipfile.ZIP_DEFLATED)
    shutil.move(tmp, out_path)
    shutil.rmtree(workdir, ignore_errors=True)
    return out_path
