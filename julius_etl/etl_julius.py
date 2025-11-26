import re, json, math, sys
from pathlib import Path
from itertools import count
from collections import Counter
import pdfplumber
from tqdm import tqdm
import pandas as pd
PDF_PATH = Path('Julius-Caesar.pdf')
OUT_JSONL = Path('julius_chunks.jsonl')
OUT_CSV = Path('julius_chunks_summary.csv')
OUT_SAMPLE = Path('julius_chunks_sample.txt')
WORD_SPLIT_THRESHOLD = 900
SENTENCE_SPLIT_THRESHOLD = 100
SOLILOQUY_MIN_WORDS = 120
FTLN_RE = re.compile('\\bFTLN\\s*\\d+\\b', flags=re.I)
PAGE_NUM_LINE_RE = re.compile('^\\s*\\d+\\s*$', flags=re.I)
HEADER_SIMPLE_RE = re.compile('(JULIUS\\s+CAESAR|THE\\s+TRAGEDY\\s+OF\\s+JULIUS\\s+CAESAR|FOLGER)', flags=re.I)
ACT_RE = re.compile('^\\s*ACT(?:\\s+|\\.?)\\s*([IVXLC]+|\\d+)\\b', flags=re.I)
SCENE_RE = re.compile('^\\s*(SC(?:ENE)?\\.?|Scene)\\s*\\.?\\s*([IVXLC]+|\\d+)\\b', flags=re.I)
ACT_SC_COMBINED_RE = re.compile('ACT\\s+([IVXLC]+|\\d+)[\\.\\s]*\\s*(?:SC(?:\\.|ENE)?\\.?)\\s*([IVXLC]+|\\d+)', re.I)
SPEAKER_LINE_RE = re.compile("^\\s*([A-Z][A-Z0-9\\s\\-\\']{1,40})\\.?\\s*(.*)")
STAGE_DIR_RE = re.compile('^\\s*(Enter|Exit|Exeunt|Scene|Sennet|Clock|Flourish|Exeunt all|They exit|He exits|She exits|Enter,|Exit,)', flags=re.I)
HEADER_LINE_REs = [re.compile('^\\s*\\d+\\s+JULIUS\\s+CAESAR.*$', re.I), re.compile('^\\s*JULIUS\\s+CAESAR.*$', re.I), re.compile('^\\s*THE\\s+TRAGEDY\\s+OF\\s+JULIUS\\s+CAESAR\\s*$', re.I), re.compile('^\\s*\\d+\\s*[-–—]?\\s*JULIUS\\s+CAESAR.*$', re.I), re.compile('^\\s*ACT\\s+\\w+\\.?\\s*SC\\.?.*$', re.I), re.compile('^\\s*SCENE\\s+\\w+.*$', re.I), re.compile('^\\s*FTLN\\s*\\d+\\s*$', re.I)]
SINGLE_LETTER_LINE = re.compile('^\\s*[A-Z]\\s*(Act|ACT)?\\b.*$', re.I)
LEADING_PAGE_RE = re.compile('^\\s*\\d+\\s*[-–—]?\\s*')
SINGLE_LET_LEAD = re.compile('(?m)^\\s*[A-Z]\\s+(?=[a-z])')
INTRO_MARKERS = ['Textual Introduction', 'Barbara Mowat', 'Paul Werstine', 'The Folger Shakespeare', 'Moby', 'digital text', 'Folger']
INTRO_RE = re.compile('|'.join((re.escape(s) for s in INTRO_MARKERS)), re.I)
ISOLATED_NUM_RE = re.compile('(?m)^\\s*\\d{1,4}\\s*$')
INLINE_SMALL_NUM_RE = re.compile('(?<=\\s)\\d{1,4}(?=\\s|[.,;:\\)\\-—])')
ACT_SC_INLINE_RE = re.compile('\\bACT\\s+[IVXLC\\d]+(?:\\.\\s*)?(?:SC(?:\\.|ENE)?\\.?\\s*[IVXLC\\d]+)?\\b', re.I)
ACT_SC_WORDS_RE = re.compile('\\bAct\\s+[IVXLC\\d]+(?:\\s+Scene\\s+[IVXLC\\d]+)?\\b', re.I)
ISOLATED_LETTER_LINE = re.compile('(?m)^\\s*[A-Z]\\s*$', re.M)
ISOLATED_LETTER_LEAD = re.compile('(?m)^\\s*[A-Z]\\s+(?=[A-Za-z])')
LEADING_SINGLE_LET_BEFORE_ACT = re.compile('(?m)\\b[A-Z]\\s+(?=(?:Act|ACT|SCENE|SC\\.)\\b)', re.I)
SINGLE_LET_BEFORE_ACT_INLINE = re.compile('\\b[A-Z]\\s+(?=Act\\b|ACT\\b|SCENE\\b|SC\\.)', re.I)

def roman_to_int(s):
    s = str(s).upper()
    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
    try:
        return int(s)
    except:
        return roman_map.get(s, s)

def sanitize_text(text: str) -> str:
    if not text:
        return ''
    txt = text
    txt = ACT_SC_INLINE_RE.sub('', txt)
    txt = ACT_SC_WORDS_RE.sub('', txt)
    txt = ISOLATED_NUM_RE.sub('', txt)
    txt = ISOLATED_LETTER_LINE.sub('', txt)
    txt = ISOLATED_LETTER_LEAD.sub('', txt)
    txt = LEADING_SINGLE_LET_BEFORE_ACT.sub('', txt)
    txt = SINGLE_LET_BEFORE_ACT_INLINE.sub('', txt)
    txt = INLINE_SMALL_NUM_RE.sub('', txt)
    txt = re.sub('\\s{2,}', ' ', txt)
    txt = re.sub('\\n{3,}', '\n\n', txt)
    return txt.strip()

def build_page_map(pdf_path: Path):
    page_map = {}
    last_act = None
    last_scene = None
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ''
            if INTRO_RE.search(text):
                page_map[pno] = (None, None)
                continue
            m_comb = ACT_SC_COMBINED_RE.search(text)
            if m_comb:
                last_act = roman_to_int(m_comb.group(1))
                last_scene = roman_to_int(m_comb.group(2))
            else:
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                for ln in lines:
                    m_act = ACT_RE.search(ln)
                    m_scene = SCENE_RE.search(ln)
                    if m_act:
                        last_act = roman_to_int(m_act.group(1))
                    if m_scene:
                        last_scene = roman_to_int(m_scene.group(2))
                    if last_act is not None and last_scene is not None:
                        break
            page_map[pno] = (last_act, last_scene)
    return page_map

def clean_page_text(text: str) -> str:
    if not text:
        return ''
    text = FTLN_RE.sub('', text)
    lines = text.splitlines()
    cleaned = []
    for ln in lines:
        s = ln.strip()
        if not s:
            cleaned.append('')
            continue
        if PAGE_NUM_LINE_RE.match(s):
            continue
        if HEADER_SIMPLE_RE.fullmatch(s):
            continue
        skip = False
        for r in HEADER_LINE_REs:
            if r.match(s):
                skip = True
                break
        if skip:
            continue
        if SINGLE_LETTER_LINE.match(s):
            continue
        if INTRO_RE.search(s):
            continue
        s = LEADING_PAGE_RE.sub('', s)
        cleaned.append(s)
    cleaned_text = '\n'.join(cleaned)
    cleaned_text = SINGLE_LET_LEAD.sub('', cleaned_text)
    cleaned_text = re.sub('(\\w+)-\\n(\\w+)', '\\1\\2', cleaned_text)
    cleaned_text = re.sub('\\n{3,}', '\n\n', cleaned_text)
    return cleaned_text.strip()

def parse_pdf(path: Path):
    page_map = build_page_map(path)
    chunks = []
    chunk_counter = count(1)
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(tqdm(pdf.pages, desc='Reading pages'), start=1):
            raw = page.extract_text() or ''
            pa_ps = page_map.get(pno, (None, None))
            if pa_ps == (None, None) and INTRO_RE.search(raw):
                continue
            cleaned_page = clean_page_text(raw)
            cleaned_page = re.sub('(?m)^\\s*[A-Z]\\s+(?=[a-z])', '', cleaned_page)
            current_act, current_scene = page_map.get(pno, (None, None))
            try:
                tables = page.extract_tables()
            except Exception:
                tables = None
            if tables:
                table_texts = []
                for table in tables:
                    for row in table:
                        row_cells = [c.strip() for c in row or [] if c and c.strip()]
                        if not row_cells:
                            continue
                        first = row_cells[0]
                        if first.isupper() and len(first) > 1 and (len(row_cells) >= 2):
                            tail = ' '.join(row_cells[1:])
                            tail = sanitize_text(tail)
                            if tail:
                                table_texts.append(f'{first}. {tail}')
                        else:
                            joined = '   '.join(row_cells)
                            joined = sanitize_text(joined)
                            if joined:
                                table_texts.append(joined)
                if table_texts:
                    cleaned_page = cleaned_page + '\n\n' + '\n'.join(table_texts)
            lines = cleaned_page.splitlines()
            i = 0
            while i < len(lines):
                raw_line = lines[i]
                line = raw_line.strip()
                if not line:
                    i += 1
                    continue
                m_line_comb = ACT_SC_COMBINED_RE.search(line)
                if m_line_comb:
                    current_act = roman_to_int(m_line_comb.group(1))
                    current_scene = roman_to_int(m_line_comb.group(2))
                    i += 1
                    continue
                am = ACT_RE.match(line)
                if am:
                    current_act = roman_to_int(am.group(1))
                    current_scene = None
                    i += 1
                    continue
                sm = SCENE_RE.match(line)
                if sm:
                    current_scene = roman_to_int(sm.group(2))
                    i += 1
                    continue
                sp_match = SPEAKER_LINE_RE.match(line)
                is_speaker = False
                speaker = None
                remainder = ''
                if sp_match:
                    candidate = sp_match.group(1).strip()
                    if candidate.isupper() and len(candidate) > 1 and (not STAGE_DIR_RE.match(candidate)):
                        is_speaker = True
                        speaker = candidate.title()
                        remainder = sp_match.group(2).strip()
                if not is_speaker and line.isupper() and (len(line) <= 80) and (not STAGE_DIR_RE.match(line)):
                    cand = line
                    if len(cand) > 1:
                        speaker = cand.title()
                        is_speaker = True
                        i += 1
                        speech_lines = []
                        while i < len(lines) and lines[i].strip() and (not lines[i].strip().isupper()):
                            speech_lines.append(lines[i].strip())
                            i += 1
                        speech_text = ' '.join(speech_lines).strip()
                        speech_text = sanitize_text(speech_text)
                        if speech_text:
                            cid = f'act{current_act}_scene{current_scene}_speech{next(chunk_counter)}'
                            add_chunk(chunks, cid, current_act, current_scene, speech_text, speaker, pno)
                    continue
                if is_speaker:
                    speech_lines = []
                    if remainder:
                        speech_lines.append(remainder)
                    j = i + 1
                    while j < len(lines):
                        nxt = lines[j].strip()
                        if not nxt:
                            j += 1
                            continue
                        if ACT_RE.match(nxt) or SCENE_RE.match(nxt):
                            break
                        nm = SPEAKER_LINE_RE.match(nxt)
                        if nm:
                            cand = nm.group(1).strip()
                            if cand.isupper() and len(cand) > 1 and (not STAGE_DIR_RE.match(cand)):
                                break
                        speech_lines.append(nxt)
                        j += 1
                    speech_text = ' '.join([l for l in speech_lines if l]).strip()
                    speech_text = sanitize_text(speech_text)
                    if speaker and speech_text:
                        cid = f'act{current_act}_scene{current_scene}_speech{next(chunk_counter)}'
                        add_chunk(chunks, cid, current_act, current_scene, speech_text, speaker, pno)
                    i = j
                    continue
                j = i
                stage_lines = []
                while j < len(lines):
                    l = lines[j].strip()
                    if not l:
                        j += 1
                        continue
                    if ACT_RE.match(l) or SCENE_RE.match(l):
                        break
                    nm = SPEAKER_LINE_RE.match(l)
                    if nm and nm.group(1).strip().isupper() and (len(nm.group(1).strip()) > 1) and (not STAGE_DIR_RE.match(nm.group(1).strip())):
                        break
                    stage_lines.append(l)
                    j += 1
                    if len(stage_lines) > 8:
                        if j < len(lines) and (not lines[j].strip()):
                            break
                stage_text = ' '.join(stage_lines).strip()
                stage_text = sanitize_text(stage_text)
                if stage_text:
                    cid = f'act{current_act}_scene{current_scene}_speech{next(chunk_counter)}'
                    add_chunk(chunks, cid, current_act, current_scene, stage_text, 'STAGE', pno)
                i = j

    def clean_chunk_text(t):
        if not t:
            return ''
        lines = t.splitlines()
        out = []
        for ln in lines:
            s = ln.strip()
            if not s:
                out.append('')
                continue
            skip = False
            for r in HEADER_LINE_REs:
                if r.match(s):
                    skip = True
                    break
            if skip:
                continue
            if SINGLE_LETTER_LINE.match(s):
                continue
            if INTRO_RE.search(s):
                continue
            s = LEADING_PAGE_RE.sub('', s)
            out.append(s)
        text = '\n'.join(out)
        text = re.sub('(?m)^\\s*[A-Z]\\s+(?=[a-z])', '', text)
        text = re.sub('(\\w+)-\\n(\\w+)', '\\1\\2', text)
        text = re.sub('\\n{3,}', '\n\n', text).strip()
        text = sanitize_text(text)
        return text
    for c in chunks:
        c['text'] = clean_chunk_text(c.get('text', ''))
        sp = c.get('speaker') or ''
        c['speaker'] = sp.strip() if isinstance(sp, str) else sp
    for c in chunks:
        if c.get('scene') is None:
            head = (c.get('text') or '')[:400]
            m = ACT_SC_COMBINED_RE.search(head)
            if m:
                try:
                    c['act'] = roman_to_int(m.group(1))
                    c['scene'] = roman_to_int(m.group(2))
                    continue
                except:
                    pass
            m2 = re.search('\\bSC(?:\\.|ENE)?\\.?\\s*([IVXLC]+|\\d+)\\b', head, re.I)
            if m2:
                try:
                    c['scene'] = roman_to_int(m2.group(1))
                except:
                    pass
    for idx, c in enumerate(chunks):
        if c.get('act') is None or c.get('scene') is None:
            for j in range(idx - 1, -1, -1):
                if chunks[j].get('act') is not None and chunks[j].get('scene') is not None:
                    c['act'] = c['act'] or chunks[j]['act']
                    c['scene'] = c['scene'] or chunks[j]['scene']
                    break
            else:
                for j in range(idx + 1, len(chunks)):
                    if chunks[j].get('act') is not None or chunks[j].get('scene') is not None:
                        c['act'] = c['act'] or chunks[j]['act']
                        c['scene'] = c['scene'] or chunks[j]['scene']
                        break

    def is_bad_speaker(name):
        if not name or not isinstance(name, str):
            return True
        n = name.strip()
        if len(n) <= 1:
            return True
        if n.upper() in {'A', 'I', 'W', 'Y', 'THE'}:
            return True
        return False
    for i, c in enumerate(chunks):
        if is_bad_speaker(c.get('speaker')):
            assigned = None
            for j in range(i - 1, -1, -1):
                if chunks[j]['act'] == c['act'] and chunks[j]['scene'] == c['scene'] and (not is_bad_speaker(chunks[j].get('speaker'))):
                    assigned = chunks[j].get('speaker')
                    break
            if assigned is None:
                for j in range(i + 1, len(chunks)):
                    if chunks[j]['act'] == c['act'] and chunks[j]['scene'] == c['scene'] and (not is_bad_speaker(chunks[j].get('speaker'))):
                        assigned = chunks[j].get('speaker')
                        break
            c['speaker'] = assigned if assigned else 'STAGE'
    merged = []
    for c in chunks:
        if merged and len(c.get('text', '').split()) <= 2:
            merged[-1]['text'] = (merged[-1]['text'] + ' ' + c.get('text', '')).strip()
        else:
            merged.append(c)
    final_post_split = []
    for c in merged:
        words = c.get('text', '').split()
        c['is_soliloquy'] = c['speaker'] != 'STAGE' and len(words) >= SOLILOQUY_MIN_WORDS
        if len(words) > WORD_SPLIT_THRESHOLD:
            parts = re.split('(?<=[.?!])\\s+(?=[A-Z])', c['text'])
            if len(parts) == 1:
                w = words
                nparts = math.ceil(len(w) / 800)
                per = math.ceil(len(w) / nparts)
                for pnum in range(nparts):
                    part_text = ' '.join(w[pnum * per:(pnum + 1) * per]).strip()
                    if part_text:
                        new = c.copy()
                        new['text'] = part_text
                        new['chunk_id'] = c['chunk_id'] + f'_part{pnum + 1}'
                        final_post_split.append(new)
            else:
                for idx, p in enumerate(parts, start=1):
                    p = p.strip()
                    if p:
                        new = c.copy()
                        new['text'] = p
                        new['chunk_id'] = c['chunk_id'] + f'_part{idx}'
                        final_post_split.append(new)
        elif len(words) > SENTENCE_SPLIT_THRESHOLD and c['speaker'] != 'STAGE':
            parts = re.split('(?<=[.?!])\\s+(?=[A-Z])', c['text'])
            if len(parts) > 1:
                for idx, p in enumerate(parts, start=1):
                    p = p.strip()
                    if p:
                        new = c.copy()
                        new['text'] = p
                        new['chunk_id'] = c['chunk_id'] + f'_sen{idx}'
                        final_post_split.append(new)
            else:
                final_post_split.append(c)
        else:
            final_post_split.append(c)
    pos = 0
    final = final_post_split
    for c in final:
        txt = c.get('text', '') or ''
        c['char_start'] = pos
        c['char_end'] = pos + len(txt)
        pos = c['char_end'] + 1
    return final

def add_chunk(chunks_list, chunk_id, act, scene, text, speaker, page):
    chunks_list.append({'play': 'Julius Caesar', 'act': act, 'scene': scene, 'speaker': speaker, 'is_soliloquy': False, 'start_page': page, 'end_page': page, 'char_start': None, 'char_end': None, 'chunk_id': chunk_id, 'text': text})

def main():
    if not PDF_PATH.exists():
        print('PDF not found. Place Julius-Caesar.pdf in the script folder.')
        sys.exit(1)
    print('Parsing PDF and building chunks (updated sanitization)...')
    chunks = parse_pdf(PDF_PATH)
    with OUT_JSONL.open('w', encoding='utf8') as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    df = pd.DataFrame([{'chunk_id': c['chunk_id'], 'act': c['act'], 'scene': c['scene'], 'speaker': c['speaker'], 'words': len(c['text'].split()), 'start_page': c['start_page'], 'end_page': c['end_page']} for c in chunks])
    df.to_csv(OUT_CSV, index=False)
    with OUT_SAMPLE.open('w', encoding='utf8') as sf:
        for c in chunks[:40]:
            sf.write(f"--- {c['chunk_id']} | {c['speaker']} | Act {c['act']} Scene {c['scene']} ---\n")
            sf.write(c['text'] + '\n\n')
    print(f'Produced {len(chunks)} chunks.')
    speaker_counts = Counter([c['speaker'] for c in chunks])
    print('Top speakers:', speaker_counts.most_common(12))
    act_counts = Counter([c['act'] for c in chunks])
    print('Act counts:', act_counts)
    print(f'JSONL: {OUT_JSONL}\nCSV: {OUT_CSV}\nSAMPLE: {OUT_SAMPLE}')
if __name__ == '__main__':
    main()