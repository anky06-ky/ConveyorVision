from pathlib import Path
from html import escape
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from pypdf import PdfReader

ROOT = Path(r'D:\Nhu\BT_03')
SRC = next(ROOT.glob('Baitapnhom5*.docx'))
DOCX_OUT = ROOT / 'Bai_tap_nhom_5_trinh_bay_theo_mau.docx'
PDF_OUT = ROOT / 'Bai_tap_nhom_5_trinh_bay_theo_mau.pdf'

# Source document contains deliberate page-break markers for the ten report
# sections. The break before the source's bibliography is removed so that the
# conclusion and references share content page 10, as the assignment allows.
BODY_START, BODY_END = 32, 118
DROP_BREAK_INDEX = 107
TOC_ROWS = [
    (0,'PHẦN MỞ ĐẦU','1'),
    (1,'1. Lý do chọn đề tài','1'),
    (1,'2. Mục tiêu và nhiệm vụ nghiên cứu','1'),
    (1,'3. Đối tượng, phạm vi và phương pháp','1'),
    (0,'CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH','2'),
    (1,'1.1. Khái niệm, bản chất và vai trò','2'),
    (1,'1.2. Cơ sở pháp lý và thời điểm áp dụng','3'),
    (1,'1.3. Điều kiện thành lập, đăng ký và hoạt động','3'),
    (1,'1.4. Nội dung hoạt động, quyền và nghĩa vụ','4'),
    (0,'CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ BẤT CẬP','5'),
    (1,'2.1. Kiểm tra hồ sơ và minh bạch thông tin','5'),
    (1,'2.2. Môi giới, thông tin sai lệch và tình huống xét xử','6'),
    (1,'2.3. Giao dịch trực tuyến và chứng cứ điện tử','7'),
    (1,'2.4. Giám sát, phối hợp và các điểm nghẽn thực thi','8'),
    (0,'CHƯƠNG III. KIẾN NGHỊ HOÀN THIỆN','9'),
    (1,'3.1. Hoàn thiện hướng dẫn và quy trình kiểm tra','9'),
    (1,'3.2. Tổ chức thực hiện và quản lý dữ liệu','9'),
    (1,'3.3. Giám sát, chế tài và bảo vệ khách hàng','9'),
    (0,'KẾT LUẬN VÀ DANH MỤC TÀI LIỆU THAM KHẢO','10'),
]

def get_text(p):
    return ' '.join(p.text.split()).replace('( ', '(').replace(' )', ')')

def set_font(run, size=13, bold=None, italic=None):
    run.font.name = 'Times New Roman'
    rpr = run._element.get_or_add_rPr()
    for key in ('ascii','hAnsi','eastAsia'):
        rpr.rFonts.set(qn('w:'+key), 'Times New Roman')
    run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic

def set_margins(sec):
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.5), Cm(2)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.5)
    sec.header_distance, sec.footer_distance = Cm(1.2), Cm(1.2)

def set_numbering(sec, fmt, start=1):
    node = sec._sectPr.find(qn('w:pgNumType'))
    if node is None:
        node = OxmlElement('w:pgNumType')
        sec._sectPr.append(node)
    node.set(qn('w:fmt'), fmt)
    node.set(qn('w:start'), str(start))

def clear_paragraph(p):
    for el in list(p._p):
        if el.tag != qn('w:pPr'):
            p._p.remove(el)

def add_field(p, instruction, fallback):
    for kind, value in [('begin',None),('instr',instruction),('separate',None),('text',fallback),('end',None)]:
        r = OxmlElement('w:r')
        if kind in ('begin','separate','end'):
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'),kind); r.append(fc)
        elif kind == 'instr':
            ins = OxmlElement('w:instrText'); ins.set(qn('xml:space'),'preserve'); ins.text = f' {value} '; r.append(ins)
        else:
            t = OxmlElement('w:t'); t.text = value; r.append(t)
        p._p.append(r)
    for run in p.runs: set_font(run,11)

def cell_margins(cell, val=55):
    tcpr=cell._tc.get_or_add_tcPr(); mar=OxmlElement('w:tcMar')
    for side in ('top','start','bottom','end'):
        el=OxmlElement('w:'+side); el.set(qn('w:w'),str(val)); el.set(qn('w:type'),'dxa'); mar.append(el)
    tcpr.append(mar)

def set_borders(table, toc=False):
    pr=table._tbl.tblPr; borders=OxmlElement('w:tblBorders')
    for side in ('top','left','bottom','right','insideH','insideV'):
        el=OxmlElement('w:'+side)
        if toc:
            el.set(qn('w:val'),'nil')
        else:
            el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'3' if toc else '5')
            el.set(qn('w:color'),'D9D9D9' if toc else '000000')
        borders.append(el)
    pr.append(borders)

def page_break_in(p):
    return any(r._r.xpath('.//w:br[@w:type="page"]') for r in p.runs)

def create_docx(src):
    old=Document(src); d=Document(); s0=d.sections[0]; set_margins(s0)
    s0.different_first_page_header_footer=True
    clear_paragraph(s0.footer.paragraphs[0]); clear_paragraph(s0.first_page_footer.paragraphs[0])
    normal=d.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(13); normal.paragraph_format.line_spacing=1.3
    for key in ('ascii','hAnsi','eastAsia'): normal._element.rPr.rFonts.set(qn('w:'+key),'Times New Roman')
    for name,size in [('Heading 1',16),('Heading 2',13)]:
        st=d.styles[name]; st.font.name='Times New Roman'; st.font.size=Pt(size); st.font.bold=True
        for key in ('ascii','hAnsi','eastAsia'): st._element.rPr.rFonts.set(qn('w:'+key),'Times New Roman')

    # Cover; text is retained from the supplied report.
    for text,size,space in [
        (get_text(old.paragraphs[1]),14,5),(get_text(old.paragraphs[2]),14,52),
        (get_text(old.paragraphs[5]),17,8),(get_text(old.paragraphs[6]),14,34),
        ('ĐỀ TÀI:',14,5),(get_text(old.paragraphs[7])+':',15,3),(get_text(old.paragraphs[8]),15,46)]:
        p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(space); p.paragraph_format.line_spacing=1.1
        set_font(p.add_run(text),size,True)
    for idx in (11,12,13):
        p=d.add_paragraph(); p.paragraph_format.left_indent=Cm(3.3); p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(5); p.paragraph_format.tab_stops.add_tab_stop(Cm(7.2),WD_TAB_ALIGNMENT.LEFT,WD_TAB_LEADER.SPACES)
        t=get_text(old.paragraphs[idx]); left,right=t.split(':',1); set_font(p.add_run(left+':\t'+right.strip()),13)
    p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(47); p.paragraph_format.first_line_indent=Cm(0)
    set_font(p.add_run(get_text(old.paragraphs[21])),13,italic=True)

    # Members / acknowledgment / declaration page.
    s1=d.add_section(WD_SECTION_START.NEW_PAGE); set_margins(s1); s1.footer.is_linked_to_previous=False; set_numbering(s1,'lowerRoman')
    f=s1.footer.paragraphs[0]; clear_paragraph(f); f.alignment=WD_ALIGN_PARAGRAPH.CENTER; add_field(f,'PAGE','i')
    def heading(text, level=2, center=True):
        p=d.add_paragraph(); p.style='Heading 1' if level==1 else 'Heading 2'
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER if center or level==1 else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_before=Pt(1 if level==2 else 0)
        p.paragraph_format.space_after=Pt(5 if level==2 else 7); p.paragraph_format.line_spacing=1.1; p.paragraph_format.keep_with_next=True
        set_font(p.add_run(text),16 if level==1 else 13,True); return p
    def body(text, ref=False):
        if ref:
            import re
            text=re.sub(r'^(\d+)\.(?=\S)',r'\1. ',text)
        p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ref else WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent=Cm(-.55) if ref else Cm(.65)
        p.paragraph_format.left_indent=Cm(.55) if ref else Cm(0)
        p.paragraph_format.space_after=Pt(4); p.paragraph_format.line_spacing=1.3
        p.paragraph_format.keep_together=True; p.paragraph_format.widow_control=True
        set_font(p.add_run(text),13); return p
    heading('DANH SÁCH THÀNH VIÊN NHÓM VÀ BẢNG PHÂN CÔNG',1)
    table=d.add_table(rows=0,cols=5); table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.autofit=False
    widths=[Cm(.9),Cm(3.4),Cm(3),Cm(6.3),Cm(1.9)]
    for ri,srow in enumerate(old.tables[0].rows):
        cells=table.add_row().cells
        for ci,cell in enumerate(cells):
            cell.width=widths[ci]; cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; cell_margins(cell)
            p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER if (ri==0 or ci in (0,2,4)) else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            set_font(p.add_run(' '.join(srow.cells[ci].text.split())),9.5 if ri else 10,ri==0)
    set_borders(table)
    heading(get_text(old.paragraphs[25]),2)
    body(get_text(old.paragraphs[26]))
    p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.RIGHT; p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(3)
    set_font(p.add_run(get_text(old.paragraphs[27])),12)
    heading(get_text(old.paragraphs[28]),2)
    body(get_text(old.paragraphs[29]))

    # One-page contents list; page values correspond to the ten content pages.
    d.add_page_break(); heading('MỤC LỤC',1)
    toc=d.add_table(rows=0,cols=2); toc.alignment=WD_TABLE_ALIGNMENT.CENTER; toc.autofit=False
    for level,label,num in TOC_ROWS:
        cells=toc.add_row().cells; cells[0].width=Cm(13.8); cells[1].width=Cm(1.1)
        for ci,c in enumerate(cells):
            cell_margins(c,20); p=c.paragraphs[0]; p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci==0 else WD_ALIGN_PARAGRAPH.RIGHT
            if ci==0 and level: p.paragraph_format.left_indent=Cm(.35)
            set_font(p.add_run(label if ci==0 else num),11.5,level==0)
    set_borders(toc,True)

    # Report body gets its own section and Arabic page numbering.
    s2=d.add_section(WD_SECTION_START.NEW_PAGE); set_margins(s2); s2.footer.is_linked_to_previous=False; set_numbering(s2,'decimal')
    f=s2.footer.paragraphs[0]; clear_paragraph(f); f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    set_font(f.add_run('Trang '),11); add_field(f,'PAGE','1'); set_font(f.add_run(' / 10'),11)
    refs=False
    for i in range(BODY_START,BODY_END+1):
        p=old.paragraphs[i]; text=get_text(p)
        if page_break_in(p):
            if i != DROP_BREAK_INDEX: d.add_page_break()
            continue
        if not text: continue
        if text == 'DANH MỤC TÀI LIỆU THAM KHẢO':
            refs=True; heading(text,2); continue
        if refs:
            body(text,ref=True); continue
        if text in ('PHẦN MỞ ĐẦU','KẾT LUẬN') or text.startswith('CHƯƠNG '):
            heading(text,1); continue
        if text[:1].isdigit() and ('. ' in text[:5] or re_heading(text)):
            heading(text,2,False); continue
        body(text)
    for sec in d.sections: set_margins(sec)
    d.core_properties.title='Kinh doanh dịch vụ sàn giao dịch bất động sản - Nhóm 5'
    d.core_properties.subject='Bài tập nhóm Khoa Luật'; d.core_properties.author='Nhóm 5'
    d.save(DOCX_OUT)
    return old

def re_heading(text):
    import re
    return bool(re.match(r'^\d+(?:\.\d+)?\.\s',text))

def pdf_fonts():
    fdir=Path(r'C:\Windows\Fonts')
    paths=[fdir/'times.ttf',fdir/'timesbd.ttf',fdir/'timesi.ttf',fdir/'timesbi.ttf']
    if not all(p.exists() for p in paths): raise FileNotFoundError('Times New Roman font files are unavailable')
    pdfmetrics.registerFont(TTFont('TNR',str(paths[0])))
    pdfmetrics.registerFont(TTFont('TNR-Bold',str(paths[1])))
    pdfmetrics.registerFont(TTFont('TNR-Italic',str(paths[2])))
    pdfmetrics.registerFont(TTFont('TNR-BoldItalic',str(paths[3])))
    pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNR-Bold',italic='TNR-Italic',boldItalic='TNR-BoldItalic')

def create_pdf(old):
    from reportlab.platypus import KeepTogether
    pdf_fonts()
    styles={
      'body':ParagraphStyle('Body',fontName='TNR',fontSize=13,leading=17,alignment=TA_JUSTIFY,firstLineIndent=.65*cm,spaceAfter=4,textColor=colors.black),
      'sub':ParagraphStyle('Sub',fontName='TNR-Bold',fontSize=13,leading=16,alignment=TA_LEFT,spaceBefore=3,spaceAfter=3,keepWithNext=True,textColor=colors.black),
      'head':ParagraphStyle('Head',fontName='TNR-Bold',fontSize=16,leading=19,alignment=TA_CENTER,spaceAfter=6,keepWithNext=True,textColor=colors.black),
      'front':ParagraphStyle('Front',fontName='TNR',fontSize=13,leading=17,alignment=TA_JUSTIFY,firstLineIndent=.65*cm,spaceAfter=4,textColor=colors.black),
      'toc':ParagraphStyle('TOC',fontName='TNR',fontSize=11.5,leading=13.2,spaceAfter=0,textColor=colors.black),
      'tocb':ParagraphStyle('TOCB',fontName='TNR-Bold',fontSize=11.5,leading=13.2,spaceAfter=0,textColor=colors.black),
      'ref':ParagraphStyle('Ref',fontName='TNR',fontSize=13,leading=17,leftIndent=.55*cm,firstLineIndent=-.55*cm,spaceAfter=4,textColor=colors.black),
      'table':ParagraphStyle('Table',fontName='TNR',fontSize=9.5,leading=11,alignment=TA_LEFT,textColor=colors.black),
      'tablec':ParagraphStyle('TableC',fontName='TNR',fontSize=9.5,leading=11,alignment=TA_CENTER,textColor=colors.black),
      'tableb':ParagraphStyle('TableB',fontName='TNR-Bold',fontSize=10,leading=11.5,alignment=TA_CENTER,textColor=colors.black),
      'cover':ParagraphStyle('Cover',fontName='TNR',fontSize=13,leading=18,alignment=TA_CENTER,spaceAfter=5,textColor=colors.black),
      'coverb':ParagraphStyle('CoverB',fontName='TNR-Bold',fontSize=14,leading=18,alignment=TA_CENTER,spaceAfter=5,textColor=colors.black),
      'covertitle':ParagraphStyle('CoverTitle',fontName='TNR-Bold',fontSize=16,leading=20,alignment=TA_CENTER,spaceAfter=7,textColor=colors.black),
      'date':ParagraphStyle('Date',fontName='TNR-Italic',fontSize=13,leading=17,alignment=TA_CENTER,spaceAfter=0,textColor=colors.black),
    }
    def para(text,style): return Paragraph(escape(text),styles[style])
    story=[]
    # Cover with the same order and white space as the sample PDF.
    cover=[get_text(old.paragraphs[i]) for i in (1,2,5,6,7,8,11,12,13,21)]
    story += [Spacer(1,1.1*cm),para(cover[0],'coverb'),para(cover[1],'coverb'),Spacer(1,1.05*cm),
              para(cover[2],'covertitle'),para(cover[3],'coverb'),Spacer(1,.45*cm),para('ĐỀ TÀI:','coverb'),
              para(cover[4]+':','coverb'),para(cover[5],'coverb'),Spacer(1,.9*cm)]
    for i in (11,12,13):
        t=get_text(old.paragraphs[i]); a,b=t.split(':',1)
        # Two-column layout without adding visual color or new information.
        story.append(Paragraph(f'<para leftIndent="{3.2*cm}">{escape(a+":")}<font name="TNR">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{escape(b.strip())}</font></para>',styles['cover']))
    story += [Spacer(1,1.05*cm),para(get_text(old.paragraphs[21]),'date'),PageBreak()]

    # Members and original front-matter text.
    story.append(para('DANH SÁCH THÀNH VIÊN NHÓM VÀ BẢNG PHÂN CÔNG','head'))
    rows=[]
    for ri,r in enumerate(old.tables[0].rows):
        row=[]
        for ci,c in enumerate(r.cells): row.append(para(' '.join(c.text.split()),'tableb' if ri==0 else ('tablec' if ci in (0,2,4) else 'table')))
        rows.append(row)
    tab=Table(rows,colWidths=[.9*cm,3.4*cm,3*cm,6.3*cm,1.9*cm],repeatRows=1,hAlign='CENTER')
    tab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.black),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story += [tab,Spacer(1,.18*cm),para(get_text(old.paragraphs[25]),'sub'),para(get_text(old.paragraphs[26]),'front'),
              Paragraph(f'<para alignment="right">{escape(get_text(old.paragraphs[27]))}</para>',styles['front']),
              para(get_text(old.paragraphs[28]),'sub'),para(get_text(old.paragraphs[29]),'front'),PageBreak()]

    # Contents table with grayscale rules and static values for ten report pages.
    story.append(para('MỤC LỤC','head'))
    tocdata=[]
    for lev,label,page in TOC_ROWS:
        st='tocb' if lev==0 else 'toc'
        left=.35*cm if lev else 0
        tocdata.append([Paragraph(f'<para leftIndent="{left}">{escape(label)}</para>',styles[st]),Paragraph(escape(page),ParagraphStyle('PageNo',parent=styles['toc'],alignment=TA_RIGHT))])
    toc=Table(tocdata,colWidths=[13.8*cm,1.1*cm],hAlign='LEFT')
    toc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),1),('RIGHTPADDING',(0,0),(-1,-1),1),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story += [toc,PageBreak()]

    # Ten body pages. Honor source page breaks except before the references.
    ref_mode=False
    for i in range(BODY_START,BODY_END+1):
        p=old.paragraphs[i]; text=get_text(p)
        if page_break_in(p):
            if i != DROP_BREAK_INDEX: story.append(PageBreak())
            continue
        if not text: continue
        if text=='DANH MỤC TÀI LIỆU THAM KHẢO':
            ref_mode=True; story.append(para(text,'sub')); continue
        if ref_mode:
            import re
            text=re.sub(r'^(\d+)\.(?=\S)',r'\1. ',text)
            story.append(para(text,'ref')); continue
        if text in ('PHẦN MỞ ĐẦU','KẾT LUẬN') or text.startswith('CHƯƠNG '):
            story.append(para(text,'head')); continue
        if re_heading(text):
            story.append(para(text,'sub')); continue
        story.append(para(text,'body'))

    class ReportTemplate(BaseDocTemplate):
        def __init__(self,path,**kw):
            super().__init__(path,**kw)
            frame=Frame(3.5*cm,2.5*cm,A4[0]-5.5*cm,A4[1]-5*cm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='main')
            self.addPageTemplates([PageTemplate(id='report',frames=[frame],onPage=self.footer)])
        def footer(self,canvas,doc):
            n=canvas.getPageNumber()
            if n in (2,3):
                canvas.saveState(); canvas.setFont('TNR',11); canvas.setFillColor(colors.black)
                canvas.drawCentredString(A4[0]/2,1.05*cm,'i' if n==2 else 'ii'); canvas.restoreState()
            elif n>=4:
                canvas.saveState(); canvas.setFont('TNR',11); canvas.setFillColor(colors.black)
                canvas.drawCentredString(A4[0]/2,1.05*cm,f'Trang {n-3} / 10'); canvas.restoreState()
    doc=ReportTemplate(str(PDF_OUT),pagesize=A4,leftMargin=3.5*cm,rightMargin=2*cm,topMargin=2.5*cm,bottomMargin=2.5*cm,
                       title='Kinh doanh dịch vụ sàn giao dịch bất động sản - Nhóm 5',author='Nhóm 5')
    doc.build(story)
    pages=len(PdfReader(PDF_OUT).pages)
    if pages != 13: raise RuntimeError(f'Expected 13 physical pages (3 front + 10 content), got {pages}')
    print('PDF_PAGES',pages)

def re_heading(text):
    import re
    return bool(re.match(r'^\d+(?:\.\d+)?\.\s',text))

if __name__=='__main__':
    original=create_docx(SRC)
    create_pdf(original)
    print('DOCX',DOCX_OUT,DOCX_OUT.stat().st_size)
    print('PDF',PDF_OUT,PDF_OUT.stat().st_size)
