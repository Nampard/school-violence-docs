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
    if d.get("학교약칭"):
        body = re.sub(r"OO고(?!등학교)", d["학교약칭"], body)
    return body


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
