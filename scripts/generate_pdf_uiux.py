"""Script tự động tạo Tài liệu Hướng dẫn Sử dụng UI/UX dạng PDF cho ConveyorVision."""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Đăng ký font tiếng Việt Arial từ hệ thống Windows
FONT_REGULAR = "Arial"
FONT_BOLD = "Arial-Bold"
FONT_ITALIC = "Arial-Italic"
FONT_BOLDITALIC = "Arial-BoldItalic"

def register_vietnamese_fonts():
    font_dir = r"C:\Windows\Fonts"
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, os.path.join(font_dir, "arial.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(font_dir, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_ITALIC, os.path.join(font_dir, "ariali.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLDITALIC, os.path.join(font_dir, "arialbi.ttf")))

class NumberedCanvas(canvas.Canvas):
    """Canvas 2 lượt để tính tổng số trang chính xác và vẽ header/footer chuyên nghiệp."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        if self._pageNumber == 1:
            # Trang bìa không vẽ header/footer
            return

        self.saveState()
        self.setFont(FONT_REGULAR, 8.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header
        self.drawString(2.0 * cm, 28.3 * cm, "CONVEYORVISION — CẨM NANG HƯỚNG DẪN SỬ DỤNG GIAO DIỆN & VẬN HÀNH UI/UX")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(2.0 * cm, 28.05 * cm, 19.0 * cm, 28.05 * cm)

        # Running Footer
        page_str = f"Trang {self._pageNumber} / {total_pages}"
        self.drawRightString(19.0 * cm, 1.2 * cm, page_str)
        self.drawString(2.0 * cm, 1.2 * cm, "ConveyorVision v2.0 • Tiêu Chuẩn HMI Công Nghiệp • Bảo Mật Nội Bộ")
        self.line(2.0 * cm, 1.5 * cm, 19.0 * cm, 1.5 * cm)

        self.restoreState()

def build_pdf(filename="doc/HUONG_DAN_SU_DUNG_UI_UX.pdf"):
    register_vietnamese_fonts()
    pdf_path = Path(filename).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm
    )

    styles = getSampleStyleSheet()

    # Định nghĩa bảng màu công nghiệp sang trọng
    PRIMARY = colors.HexColor("#0f172a")     # Deep navy slate
    BRAND_BLUE = colors.HexColor("#0284c7")  # Cyan/Sky blue
    PASS_GREEN = colors.HexColor("#10b981")  # Emerald
    DEFECT_RED = colors.HexColor("#ef4444")  # Crimson
    OTHER_PURPLE = colors.HexColor("#8b5cf6")# Violet
    AMBER_GOLD = colors.HexColor("#f59e0b")  # Amber
    TEXT_DARK = colors.HexColor("#1e293b")   # Slate 800
    TEXT_MUTED = colors.HexColor("#64748b")  # Slate 500
    BG_LIGHT = colors.HexColor("#f8fafc")    # Slate 50
    BORDER_LIGHT = colors.HexColor("#e2e8f0")# Slate 200

    # Custom Typography Styles
    styles.add(ParagraphStyle(
        "CoverTag",
        fontName=FONT_BOLD,
        fontSize=10,
        leading=13,
        textColor=BRAND_BLUE,
        alignment=0,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        "CoverTitle",
        fontName=FONT_BOLD,
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        "CoverSubtitle",
        fontName=FONT_REGULAR,
        fontSize=12.5,
        leading=18,
        textColor=TEXT_MUTED,
        alignment=0,
        spaceAfter=25
    ))
    styles.add(ParagraphStyle(
        "DocH1",
        fontName=FONT_BOLD,
        fontSize=15,
        leading=20,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=7,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        "DocH2",
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=BRAND_BLUE,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        "DocH3",
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=TEXT_DARK,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        "DocBody",
        fontName=FONT_REGULAR,
        fontSize=9.5,
        leading=14.5,
        textColor=TEXT_DARK,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        "DocBodyBold",
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=14.5,
        textColor=TEXT_DARK,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        "DocBullet",
        fontName=FONT_REGULAR,
        fontSize=9.5,
        leading=14,
        textColor=TEXT_DARK,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        "CalloutText",
        fontName=FONT_REGULAR,
        fontSize=9.0,
        leading=13.5,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        "TableHeader",
        fontName=FONT_BOLD,
        fontSize=9.0,
        leading=12,
        textColor=colors.white,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        "TableCell",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        "TableCellBold",
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK
    ))
    styles.add(ParagraphStyle(
        "TableCellCenter",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        "MetaLabel",
        fontName=FONT_BOLD,
        fontSize=9,
        leading=13,
        textColor=TEXT_MUTED
    ))
    styles.add(ParagraphStyle(
        "MetaVal",
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK
    ))

    story = []

    # =========================================================================
    # TRANG BÌA (COVER PAGE)
    # =========================================================================
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("HỆ THỐNG KIỂM ĐỊNH THỊ GIÁC MÁY TÍNH CONVEYORVISION 2.0", styles["CoverTag"]))
    story.append(Paragraph("TÀI LIỆU HƯỚNG DẪN SỬ DỤNG GIAO DIỆN & VẬN HÀNH UI/UX", styles["CoverTitle"]))
    story.append(Paragraph(
        "Cẩm nang hướng dẫn thao tác toàn diện trên Web Dashboard dành cho Kỹ sư Vận hành, "
        "Giám sát Dây chuyền và Chuyên viên Đảm bảo Chất lượng (QA/QC).",
        styles["CoverSubtitle"]
    ))

    story.append(HRFlowable(width="100%", thickness=2.5, color=BRAND_BLUE, spaceBefore=0, spaceAfter=20))

    # Bảng Metadata
    meta_data = [
        [Paragraph("Mã tài liệu:", styles["MetaLabel"]), Paragraph("<b>CV-HMI-DOC-2026-V2</b>", styles["MetaVal"])],
        [Paragraph("Phiên bản hệ thống:", styles["MetaLabel"]), Paragraph("<b>ConveyorVision 2.0.0 (Băng Chuyền Đa Vật Thể)</b>", styles["MetaVal"])],
        [Paragraph("Tiêu chuẩn áp dụng:", styles["MetaLabel"]), Paragraph("ISO 9241-210 (Human-Centered Design) & Industrial HMI Standard", styles["MetaVal"])],
        [Paragraph("Kiến trúc giao diện:", styles["MetaLabel"]), Paragraph("Single Page Application (FastAPI + Modern Dark Glassmorphism)", styles["MetaVal"])],
        [Paragraph("Tốc độ & Độ trễ:", styles["MetaLabel"]), Paragraph("<b>22–25 FPS (CPU)</b> • Độ trễ video hiển thị: <b>&lt; 50 ms</b>", styles["MetaVal"])],
        [Paragraph("Ngày phát hành:", styles["MetaLabel"]), Paragraph("Tháng 10 / 2026", styles["MetaVal"])],
        [Paragraph("Đơn vị biên soạn:", styles["MetaLabel"]), Paragraph("Đội ngũ Kỹ sư Phần mềm & Thị Giác Máy Tính ConveyorVision", styles["MetaVal"])],
        [Paragraph("Trạng thái tài liệu:", styles["MetaLabel"]), Paragraph("<font color='#10b981'><b>ĐÃ PHÊ DUYỆT BAN HÀNH CHÍNH THỨC</b></font>", styles["MetaVal"])],
    ]
    t_meta = Table(meta_data, colWidths=[4.2 * cm, 12.8 * cm])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_meta)

    story.append(Spacer(1, 1.2 * cm))

    # Hộp Callout Giới thiệu nhanh
    callout_intro = [
        [
            Paragraph(
                "<b>Mục tiêu của tài liệu này:</b><br/>"
                "Cung cấp hướng dẫn trực quan, chuẩn hóa từng thao tác trên bảng điều khiển HMI, "
                "từ việc tải nguồn video, chọn chế độ phân loại <i>(Chai &amp; Dị vật khác vs QC Chai chuyên sâu)</i>, "
                "đọc hiểu các chỉ số và cờ cảnh báo thời gian thực, cho đến quản lý dữ liệu kiểm toán CSV "
                "và xử lý nhanh các tình huống sự cố thường gặp trong sản xuất.",
                styles["CalloutText"]
            )
        ]
    ]
    t_callout = Table(callout_intro, colWidths=[17.0 * cm])
    t_callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ("BOX", (0, 0), (-1, -1), 1.5, PASS_GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(t_callout)

    story.append(PageBreak())

    # =========================================================================
    # CHƯƠNG 1: TRIẾT LÝ THIẾT KẾ UI/UX & CHUẨN HMI CÔNG NGHIỆP
    # =========================================================================
    story.append(Paragraph("1. Triết Lý Thiết Kế UI/UX &amp; Chuẩn HMI Công Nghiệp", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Giao diện điều khiển <b>ConveyorVision Web Dashboard</b> được phát triển dựa trên nguyên lý "
        "<b>Human-Machine Interface (HMI)</b> chuyên dụng cho nhà máy tự động hóa, đáp ứng các tiêu chí vận hành khắt khe:",
        styles["DocBody"]
    ))

    story.append(Paragraph("• <b>Bảng màu Dark Navy Slate chống mỏi mắt:</b> Môi trường nhà xưởng và trạm kiểm soát đòi hỏi kỹ sư theo dõi màn hình liên tục từ 8 đến 12 giờ mỗi ca. Tông nền tối (#090d16 / #0f172a) kết hợp lớp kính mờ Glassmorphism giúp loại bỏ độ chói lóa, tăng độ tập trung vào khung hình camera.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Mã màu trạng thái trực quan tiêu chuẩn quốc tế:</b>", styles["DocBullet"]))

    color_table_data = [
        [Paragraph("Màu Sắc &amp; Mã Hex", styles["TableHeader"]), Paragraph("Ý Nghĩa Vận Hành", styles["TableHeader"]), Paragraph("Áp Dụng Trong Hệ Thống", styles["TableHeader"])],
        [
            Paragraph("<font color='#10b981'><b>Emerald Green (#10b981)</b></font>", styles["TableCellBold"]),
            Paragraph("ĐẠT CHUẨN (PASS) / SẴN SÀNG", styles["TableCellBold"]),
            Paragraph("Chai đạt tiêu chuẩn QC, worker đang chạy, thông báo thành công.", styles["TableCell"])
        ],
        [
            Paragraph("<font color='#ef4444'><b>Crimson Red (#ef4444)</b></font>", styles["TableCellBold"]),
            Paragraph("PHẾ PHẨM (DEFECT) / BÁO LỖI", styles["TableCellBold"]),
            Paragraph("Chai móp méo, rách nhãn, thiếu nắp, worker lỗi, cờ loại bỏ khẩn cấp.", styles["TableCell"])
        ],
        [
            Paragraph("<font color='#8b5cf6'><b>Royal Violet (#8b5cf6)</b></font>", styles["TableCellBold"]),
            Paragraph("DỊ VẬT / ĐỒ VẬT KHÁC (OTHER)", styles["TableCellBold"]),
            Paragraph("Đồ vật rơi vào băng tải (cốc, hộp, lon, bút...), khoanh viền tím phân biệt.", styles["TableCell"])
        ],
        [
            Paragraph("<font color='#f59e0b'><b>Amber Gold (#f59e0b)</b></font>", styles["TableCellBold"]),
            Paragraph("ĐANG QUÉT / TẠM DỪNG (PAUSE)", styles["TableCellBold"]),
            Paragraph("Vật thể chưa đủ số frame xác nhận, hệ thống đang tạm dừng quan sát.", styles["TableCell"])
        ],
        [
            Paragraph("<font color='#0284c7'><b>Industrial Cyan (#0284c7)</b></font>", styles["TableCellBold"]),
            Paragraph("THÔNG SỐ &amp; TỶ LỆ KỸ THUẬT", styles["TableCellBold"]),
            Paragraph("Thanh tiến trình, tỷ lệ %, phím điều hướng, độ trễ và tốc độ FPS.", styles["TableCell"])
        ]
    ]
    t_colors = Table(color_table_data, colWidths=[4.2 * cm, 4.8 * cm, 8.0 * cm])
    t_colors.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_colors)

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("• <b>Cập nhật tại chỗ phản ứng nhanh (In-place Reactive DOM):</b> Ứng dụng kết nối WebSocket trực tiếp tới backend máy chủ. Mỗi khi có vật thể mới hoặc trạng thái chai được cập nhật từ <i>Đang quét</i> sang <i>DEFECT/PASS</i>, dòng dữ liệu trên bảng sự kiện chỉ chớp sáng và cập nhật đúng ô nhớ đó, hoàn toàn không nạp lại trang hay tạo dòng thừa gây rối mắt.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Độ trễ truyền hình ảnh cực thấp (&lt; 50ms):</b> Luồng MJPEG Stream áp dụng cơ chế <i>Condition Variable</i> và <i>Wall-clock Pacing</i>. Khi chọn chế độ 480px, tốc độ hiển thị đạt 22–25 FPS mượt mà ngay trên CPU máy tính văn phòng thông thường.", styles["DocBullet"]))

    # =========================================================================
    # CHƯƠNG 2: CẤU TRÚC ĐIỀU HƯỚNG & 6 PHÂN HỆ MÀN HÌNH
    # =========================================================================
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("2. Cấu Trúc Điều Hướng &amp; 6 Phân Hệ Chức Năng", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Hệ thống tổ chức theo mô hình Single Page Application (SPA) gồm 6 màn hình chuyên biệt "
        "thông qua thanh Menu điều hướng bên trái:",
        styles["DocBody"]
    ))

    screens_data = [
        [Paragraph("Phân Hệ Màn Hình", styles["TableHeader"]), Paragraph("Mục Đích &amp; Chức Năng Chính", styles["TableHeader"]), Paragraph("Đối Tượng Phục Vụ", styles["TableHeader"])],
        [
            Paragraph("<b>1. Tổng Quan</b><br/><i>(Overview)</i>", styles["TableCellBold"]),
            Paragraph("Theo dõi 4 thẻ KPI vĩ mô tích lũy (Tổng quét, PASS, DEFECT, Tỷ lệ lỗi). Xem bảng nhật ký 5 phiên gần nhất và các thông số phần cứng.", styles["TableCell"]),
            Paragraph("Trưởng ca sản xuất, Giám đốc chất lượng", styles["TableCell"])
        ],
        [
            Paragraph("<b>2. Kiểm Định Trực Tiếp</b><br/><i>(Live Inspection)</i>", styles["TableCellBold"]),
            Paragraph("<b>Trọng tâm vận hành:</b> Stream camera trực tiếp, thanh điều khiển 2 tầng, HUD nhận diện đa vật thể, cờ loại bỏ phế phẩm, còi âm thanh Web Audio và bảng sự kiện thời gian thực.", styles["TableCell"]),
            Paragraph("Kỹ sư vận hành máy, Nhân viên kiểm soát QC", styles["TableCell"])
        ],
        [
            Paragraph("<b>3. Lịch Sử Kiểm Định</b><br/><i>(Inspection History)</i>", styles["TableCellBold"]),
            Paragraph("Tra cứu toàn bộ các ca sản xuất trong quá khứ. Mở modal kiểm tra từng mã Track ID và tải file kiểm toán CSV chi tiết từng mili-giây.", styles["TableCell"]),
            Paragraph("Bộ phận Quản lý Chất lượng, Kiểm toán ISO/HACCP", styles["TableCell"])
        ],
        [
            Paragraph("<b>4. Đánh Giá Mô Hình</b><br/><i>(Model Evaluation)</i>", styles["TableCellBold"]),
            Paragraph("Xem bảng chỉ số Precision/Recall/mAP trên tập Test độc lập, minh bạch khoa học về ảnh cận trùng, đo benchmark độ trễ suy luận và biểu đồ PR-Curve phóng to toàn màn hình.", styles["TableCell"]),
            Paragraph("Kỹ sư AI, Chuyên gia Thị giác Máy tính", styles["TableCell"])
        ],
        [
            Paragraph("<b>5. Dữ Liệu &amp; Mô Hình</b><br/><i>(Dataset &amp; Models)</i>", styles["TableCellBold"]),
            Paragraph("Thống kê quy mô phân bổ 2.666 ảnh chuẩn hóa (Train/Val/Test) và danh mục các file trọng số (.pt) có sẵn trong trạm.", styles["TableCell"]),
            Paragraph("Kỹ sư AI, Quản trị hệ thống", styles["TableCell"])
        ],
        [
            Paragraph("<b>6. Cài Đặt Tham Số</b><br/><i>(System Settings)</i>", styles["TableCellBold"]),
            Paragraph("Cấu hình thuật toán ByteTrack/BoT-SORT, ngưỡng mất dấu (Lost Buffer), số frame quan sát tối thiểu, còi buzzer và tự động xuất CSV.", styles["TableCell"]),
            Paragraph("Kỹ thuật viên bảo trì, Trưởng ca", styles["TableCell"])
        ],
    ]
    t_screens = Table(screens_data, colWidths=[3.8 * cm, 9.2 * cm, 4.0 * cm])
    t_screens.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_screens)

    story.append(PageBreak())

    # =========================================================================
    # CHƯƠNG 3: HƯỚNG DẪN VẬN HÀNH CHI TIẾT MÀN HÌNH TRỰC TIẾP
    # =========================================================================
    story.append(Paragraph("3. Hướng Dẫn Vận Hành Màn Hình Kiểm Định Trực Tiếp", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Màn hình <b>Kiểm định trực tiếp (Live Inspection)</b> là nơi diễn ra mọi hoạt động giám sát "
        "thời gian thực. Quy trình vận hành chuẩn gồm 3 bước sau:",
        styles["DocBody"]
    ))

    story.append(Paragraph("Bước 1: Thiết Lập Nguồn &amp; Chế Độ Kiểm Định", styles["DocH2"]))
    story.append(Paragraph("Trước khi bấm khởi động, người vận hành cần cấu hình tại <b>Thanh điều khiển Cockpit 2 tầng</b>:", styles["DocBody"]))

    story.append(Paragraph("1. <b>Chọn Nguồn Video:</b>", styles["DocBodyBold"]))
    story.append(Paragraph("• <i>Video Demo (Mô phỏng):</i> Chạy video băng chuyền mẫu chuẩn hóa có sẵn.", styles["DocBullet"]))
    story.append(Paragraph("• <i>Webcam 0 (USB Camera):</i> Thu trực tiếp từ camera gắn trên trạm kiểm định băng tải.", styles["DocBullet"]))
    story.append(Paragraph("• <i>Tải video tự quay lên:</i> Bấm nút <code>Choose File</code> để tải file video quay thực tế (.mp4, .avi, .mov). Hệ thống tự chuẩn hóa tên an toàn và tự chọn file vào danh sách nguồn.", styles["DocBullet"]))

    story.append(Paragraph("2. <b>Lựa Chọn Chế Độ Kiểm Định (Đặc biệt quan trọng):</b>", styles["DocBodyBold"]))

    mode_data = [
        [Paragraph("Chế Độ Kiểm Định", styles["TableHeader"]), Paragraph("Mô Tả Thuật Toán &amp; Hành Vi", styles["TableHeader"]), Paragraph("Khi Nào Nên Dùng?", styles["TableHeader"])],
        [
            Paragraph("<font color='#8b5cf6'><b>🍶 Chai &amp; Dị Vật Khác<br/>(Tự Quay / Đa Vật Thể)</b></font>", styles["TableCellBold"]),
            Paragraph("Mô hình tự động phân tách <b>Chai lọ</b> (viền Xanh/Đỏ tùy chất lượng) và <b>Các vật thể lạ khác</b> trên băng chuyền (cốc, hộp, lon, sách, điện thoại... viền Tím hồng). Đếm riêng vào mục <i>Dị vật</i>, không bị phạt nhầm thành phế phẩm.", styles["TableCell"]),
            Paragraph("<b>Khuyên dùng cho video thực tế tự quay bằng điện thoại</b> hoặc băng tải hỗn hợp nhiều chủng loại sản phẩm.", styles["TableCellBold"])
        ],
        [
            Paragraph("<font color='#0284c7'><b>🔍 QC Chai Đạt / Lỗi<br/>(Chuyên Sâu)</b></font>", styles["TableCellBold"]),
            Paragraph("Mô hình tập trung 100% tài nguyên thuật toán vào việc phát hiện khuyết tật chuyên sâu trên chai lọ: móp thân, rách nhãn, lệch nắp, vơi mức nước chai (viền Đỏ - DEFECT vs viền Xanh - PASS).", styles["TableCell"]),
            Paragraph("Dùng cho dây chuyền sản xuất đóng chai tiêu chuẩn, phôi chai đồng nhất.", styles["TableCell"])
        ]
    ]
    t_mode = Table(mode_data, colWidths=[4.2 * cm, 8.8 * cm, 4.0 * cm])
    t_mode.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_mode)

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("3. <b>Độ Phân Giải Suy Luận:</b>", styles["DocBodyBold"]))
    story.append(Paragraph("• <code>⚡ 480px (Siêu mượt)</code>: <b>Lựa chọn khuyên dùng khi chạy trên CPU</b>. Giảm 50% tải tính toán, tốc độ tăng vọt lên 22–25 FPS, triệt tiêu hiện tượng lag hình.", styles["DocBullet"]))
    story.append(Paragraph("• <code>🎯 640px (Chuẩn)</code>: Dành cho máy tính trạm có card đồ họa rời GPU NVIDIA hoặc khi cần soi chi tiết khuyết tật siêu nhỏ.", styles["DocBullet"]))

    story.append(Paragraph("4. <b>Ngưỡng Tin Cậy (Confidence Slider):</b> Dải giá trị từ <code>0.10</code> đến <code>0.90</code> (mặc định: <code>0.45</code>). Kéo sang phải để loại bỏ báo động giả; kéo sang trái để nhạy hơn với các vết nứt mờ.", styles["DocBody"]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Bước 2: Vận Hành Kiểm Tra &amp; Điều Khiển", styles["DocH2"]))

    ops_data = [
        [Paragraph("Thao Tác", styles["TableHeader"]), Paragraph("Hành Vi Hệ Thống", styles["TableHeader"]), Paragraph("Mẹo Vận Hành", styles["TableHeader"])],
        [
            Paragraph("<b>▶ Bắt Đầu</b>", styles["TableCellBold"]),
            Paragraph("Khởi tạo worker nền, kết nối camera, bắt đầu luồng MJPEG và kích hoạt WebSocket.", styles["TableCell"]),
            Paragraph("Nút lập tức chuyển trạng thái, không bị treo giao diện.", styles["TableCell"])
        ],
        [
            Paragraph("<b>⏸ Tạm Dừng</b>", styles["TableCellBold"]),
            Paragraph("Đóng băng tạm thời khung hình camera tại thời điểm bấm, giữ nguyên trạng thái các track ID.", styles["TableCell"]),
            Paragraph("Dùng khi cần dừng mắt soi kỹ một chai nghi vấn trên băng tải.", styles["TableCell"])
        ],
        [
            Paragraph("<b>📸 Chụp Hiện Trường</b>", styles["TableCellBold"]),
            Paragraph("Lưu ngay lập tức ảnh chụp nguyên độ phân giải kèm khung bounding box vào thư mục <code>reports/snapshots/</code>.", styles["TableCell"]),
            Paragraph("Lập tức hiển thị ảnh thumbnail bên phải màn hình để xem lại.", styles["TableCell"])
        ],
        [
            Paragraph("<b>⏹ Dừng Phiên</b>", styles["TableCellBold"]),
            Paragraph("Kết thúc phiên làm việc, chốt toàn bộ số liệu thống kê cuối cùng và tự động xuất file log CSV kiểm toán.", styles["TableCell"]),
            Paragraph("Đóng phiên an toàn trước khi chuyển sang ca tiếp theo.", styles["TableCell"])
        ],
        [
            Paragraph("<b>⛶ Phóng To</b>", styles["TableCellBold"]),
            Paragraph("Mở khung hình camera ở chế độ toàn màn hình (Fullscreen) không viền.", styles["TableCell"]),
            Paragraph("Phù hợp hiển thị trên màn hình TV lớn treo trên trạm xưởng.", styles["TableCell"])
        ],
    ]
    t_ops = Table(ops_data, colWidths=[3.2 * cm, 8.8 * cm, 5.0 * cm])
    t_ops.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_ops)

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Bước 3: Đọc Hiểu HUD Video &amp; Bảng Sự Kiện Thời Gian Thực", styles["DocH2"]))

    # Kiểm tra và nhúng ảnh snapshot minh họa nếu có
    snapshot_path = Path("reports/snapshots/snapshot_20261025_113348.jpg")
    if not snapshot_path.exists():
        eval_img = Path("doc/evaluation/test_batch0_pred.jpg")
        if eval_img.exists():
            snapshot_path = eval_img

    if snapshot_path.exists():
        story.append(Paragraph("<i>Hình 1: Trực quan hóa Bounding Box, Track ID và HUD phân loại trên băng chuyền:</i>", styles["DocBodyBold"]))
        story.append(Image(str(snapshot_path), width=16.5 * cm, height=6.5 * cm))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("• <b>Khung viền Bounding Box:</b> Màu sắc tương ứng chuẩn (Xanh lá: PASS, Đỏ: DEFECT, Tím: Dị vật khác). Trên mỗi khung hiển thị <code>#ID Nhãn Confidence</code> (ví dụ: <code>#12 pass 0.94</code> hoặc <code>#15 defect 0.88</code>).", styles["DocBullet"]))
    story.append(Paragraph("• <b>Cờ cảnh báo loại bỏ (Hazard Banner):</b> Khi phát hiện sản phẩm lỗi, banner đỏ nhấp nháy <i>'CẢNH BÁO: PHÁT HIỆN SẢN PHẨM KHUYẾT TẬT - KÍCH HOẠT CƠ CẤU LOẠI BỎ'</i> sẽ bật sáng ngay trên đầu video.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Còi báo động Web Audio API:</b> Tự động phát âm thanh cảnh báo kép công nghiệp (880Hz &rarr; 440Hz). Kỹ sư có thể tắt/bật còi bất kỳ lúc nào bằng công tắc âm thanh bên cạnh bảng số liệu.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Bảng nhật ký sản phẩm (Event Log):</b> Cập nhật tại chỗ. Khi sản phẩm có thêm bằng chứng đổi trạng thái từ đang quan sát sang DEFECT, dòng tương ứng sẽ chớp sáng xanh và cập nhật ngay lập tức.", styles["DocBullet"]))

    story.append(PageBreak())

    # =========================================================================
    # CHƯƠNG 4: QUẢN LÝ LỊCH SỬ KIỂM ĐỊNH & KIỂM TOÁN DỮ LIỆU
    # =========================================================================
    story.append(Paragraph("4. Quản Lý Lịch Sử Kiểm Định &amp; Kiểm Toán CSV", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Mọi ca sản xuất đều được hệ thống lưu trữ có cấu trúc phục vụ công tác truy xuất nguồn gốc "
        "và kiểm toán chất lượng theo tiêu chuẩn quốc tế ISO 9001 / HACCP.",
        styles["DocBody"]
    ))

    story.append(Paragraph("4.1. Bảng Tổng Hợp Lịch Sử (Inspection History)", styles["DocH2"]))
    story.append(Paragraph(
        "Tại màn hình <b>Lịch sử kiểm định</b>, danh sách các phiên được sắp xếp theo thời gian mới nhất. "
        "Mỗi dòng ghi nhận: Mã phiên (Session ID), Nguồn video/camera, Thời điểm bắt đầu, Tổng sản phẩm quét, "
        "Số lượng PASS, Số lượng DEFECT và Tỷ lệ phế phẩm (%).",
        styles["DocBody"]
    ))

    story.append(Paragraph("4.2. Xem Chi Tiết Từng Mã Track ID (Audit Modal)", styles["DocH2"]))
    story.append(Paragraph(
        "Nhấp vào nút <b>'Chi tiết'</b> tại bất kỳ phiên nào để mở cửa sổ kiểm toán chuyên sâu. "
        "Bảng chi tiết cung cấp hồ sơ từng sản phẩm:",
        styles["DocBody"]
    ))
    story.append(Paragraph("• <code>Track ID</code>: Định danh duy nhất của sản phẩm trong suốt hành trình qua camera.", styles["DocBullet"]))
    story.append(Paragraph("• <code>Max Confidence</code>: Mức độ tin cậy cao nhất mà mô hình AI ghi nhận được.", styles["DocBullet"]))
    story.append(Paragraph("• <code>First Seen / Last Seen</code>: Thời điểm chính xác (đến mili-giây) chai xuất hiện và rời khỏi tầm quét.", styles["DocBullet"]))
    story.append(Paragraph("• <code>Observation Frames</code>: Tổng số khung hình camera quan sát được vật thể.", styles["DocBullet"]))
    story.append(Paragraph("• <code>Trạng thái chốt</code>: Kết luận cuối cùng (Đạt chuẩn hoặc Phế phẩm).", styles["DocBullet"]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("4.3. Xuất &amp; Tải File Báo Cáo CSV", styles["DocH2"]))
    story.append(Paragraph(
        "Bấm nút <b>'Tải CSV'</b> để tải tệp dữ liệu bảng tính. Tệp CSV được định dạng chuẩn, "
        "có thể mở trực tiếp bằng Microsoft Excel, Google Sheets hoặc nạp vào hệ thống ERP / MES của nhà máy.",
        styles["DocBody"]
    ))

    # =========================================================================
    # CHƯƠNG 5: ĐÁNH GIÁ MÔ HÌNH & THÔNG SỐ CÀI ĐẶT
    # =========================================================================
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("5. Đánh Giá Mô Hình &amp; Tùy Biến Cài Đặt", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("5.1. Màn Hình Đánh Giá (Model Evaluation)", styles["DocH2"]))
    story.append(Paragraph(
        "Màn hình này công khai minh bạch toàn bộ năng lực định lượng của mô hình YOLO26 Nano trên 441 ảnh Test độc lập:",
        styles["DocBody"]
    ))
    story.append(Paragraph("• <b>Độ chính xác:</b> mAP@50 đạt <b>0.995 (99.5%)</b>, F1-Score đạt <b>0.98</b> tại ngưỡng conf=0.45.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Tốc độ xử lý:</b> Thời gian tiền xử lý 3.1ms, suy luận 125.9ms (CPU thông thường) / 10–15ms (dự kiến GPU), hậu xử lý 2.4ms.", styles["DocBullet"]))
    story.append(Paragraph("• <b>Phóng to biểu đồ:</b> Người dùng có thể nhấp chuột trực tiếp vào bất kỳ biểu đồ nào (PR-Curve, Confusion Matrix, Loss) để phóng to toàn màn hình.", styles["DocBullet"]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("5.2. Màn Hình Cài Đặt Tham Số (Settings)", styles["DocH2"]))

    settings_data = [
        [Paragraph("Tham Số", styles["TableHeader"]), Paragraph("Ý Nghĩa Kỹ Thuật", styles["TableHeader"]), Paragraph("Giá Trị Chuẩn", styles["TableHeader"])],
        [
            Paragraph("<b>Thuật toán Tracking</b>", styles["TableCellBold"]),
            Paragraph("Lựa chọn ByteTrack (nhẹ, nhanh, tối ưu chuyển động thẳng) hoặc BoT-SORT (kèm bù chuyển động khi camera rung).", styles["TableCell"]),
            Paragraph("<code>ByteTrack</code>", styles["TableCellCenter"])
        ],
        [
            Paragraph("<b>Ngưỡng Mất Dấu<br/>(Lost Buffer)</b>", styles["TableCellBold"]),
            Paragraph("Số frame liên tiếp camera không thấy vật thể trước khi chính thức chốt PASS và giải phóng ID.", styles["TableCell"]),
            Paragraph("<code>30 frames</code>", styles["TableCellCenter"])
        ],
        [
            Paragraph("<b>Số Lượt Quan Sát<br/>(Min Votes)</b>", styles["TableCellBold"]),
            Paragraph("Số khung hình tối thiểu cần quan sát trước khi đưa ra kết luận, loại bỏ nhiễu biên mép camera.", styles["TableCell"]),
            Paragraph("<code>3 frames</code>", styles["TableCellCenter"])
        ],
        [
            Paragraph("<b>Tự Động Xuất CSV</b>", styles["TableCellBold"]),
            Paragraph("Tự động lưu file log chi tiết sau mỗi phiên kiểm định vào thư mục <code>reports/</code>.", styles["TableCell"]),
            Paragraph("<code>BẬT (True)</code>", styles["TableCellCenter"])
        ],
    ]
    t_set = Table(settings_data, colWidths=[3.8 * cm, 9.2 * cm, 4.0 * cm])
    t_set.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_set)

    story.append(PageBreak())

    # =========================================================================
    # CHƯƠNG 6: BẢNG PHÍM TẮT & THAO TÁC NHANH
    # =========================================================================
    story.append(Paragraph("6. Bảng Phím Tắt &amp; Thao Tác Nhanh (Shortcuts)", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Nhằm tăng năng suất cho kỹ sư vận hành tại hiện trường, hệ thống hỗ trợ đầy đủ các phím tắt nhanh:",
        styles["DocBody"]
    ))

    shortcut_data = [
        [Paragraph("Phím Bấm / Cử Chỉ", styles["TableHeader"]), Paragraph("Khu Vực Tác Động", styles["TableHeader"]), Paragraph("Chức Năng Thực Hiện", styles["TableHeader"])],
        [
            Paragraph("<b>Bấm Logo ConveyorVision</b>", styles["TableCellBold"]),
            Paragraph("Góc trên bên trái", styles["TableCell"]),
            Paragraph("Quay nhanh về Màn hình 1: Tổng quan (Overview).", styles["TableCell"])
        ],
        [
            Paragraph("<b>Nút 📥 Báo Cáo Kỹ Thuật</b>", styles["TableCellBold"]),
            Paragraph("Thanh Header góc trên", styles["TableCell"]),
            Paragraph("Tải ngay toàn văn Bản Báo Cáo Nghiệm Thu Kỹ Thuật (PDF) về máy tính.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Nút 📘 Hướng Dẫn UI/UX</b>", styles["TableCellBold"]),
            Paragraph("Thanh Header góc trên", styles["TableCell"]),
            Paragraph("Tải ngay Cẩm Nang Hướng Dẫn Sử Dụng Giao Diện &amp; Vận Hành UI/UX (PDF).", styles["TableCell"])
        ],
        [
            Paragraph("<b>Nút 📖 Cẩm Nang Online</b>", styles["TableCellBold"]),
            Paragraph("Thanh Header góc trên", styles["TableCell"]),
            Paragraph("Mở hộp thoại Modal tra cứu hướng dẫn tương tác 5 tab ngay trong ứng dụng.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Phím ESC (Escape)</b>", styles["TableCellBold"]),
            Paragraph("Toàn hệ thống", styles["TableCell"]),
            Paragraph("Đóng tức thì bất kỳ cửa sổ Modal, hộp thoại chi tiết hoặc phóng to biểu đồ nào đang mở.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Phím 1, 2, 3, 4, 5, 6</b>", styles["TableCellBold"]),
            Paragraph("Bàn phím", styles["TableCell"]),
            Paragraph("Chuyển nhanh lần lượt giữa 6 màn hình chức năng của hệ thống.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Phím F / Nút ⛶</b>", styles["TableCellBold"]),
            Paragraph("Khung video camera", styles["TableCell"]),
            Paragraph("Bật / tắt chế độ toàn màn hình Fullscreen không viền.", styles["TableCell"])
        ],
        [
            Paragraph("<b>Nhấp đúp ảnh biểu đồ</b>", styles["TableCellBold"]),
            Paragraph("Màn hình Đánh giá", styles["TableCell"]),
            Paragraph("Mở cửa sổ phóng đại độ nét cao để soi chi tiết tọa độ trục biểu đồ.", styles["TableCell"])
        ],
    ]
    t_short = Table(shortcut_data, colWidths=[4.2 * cm, 4.0 * cm, 8.8 * cm])
    t_short.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_short)

    # =========================================================================
    # CHƯƠNG 7: CẨM NANG XỬ LÝ SỰ CỐ (TROUBLESHOOTING)
    # =========================================================================
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("7. Cẩm Nang Chẩn Đoán &amp; Xử Lý Sự Cố (Troubleshooting)", styles["DocH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Bảng hướng dẫn kỹ thuật viên xử lý nhanh 5 tình huống thường phát sinh tại trạm kiểm định:",
        styles["DocBody"]
    ))

    trouble_data = [
        [Paragraph("Hiện Tượng Sự Cố", styles["TableHeader"]), Paragraph("Nguyên Nhân Khả Dĩ", styles["TableHeader"]), Paragraph("Quy Trình Xử Lý Nhanh", styles["TableHeader"])],
        [
            Paragraph("<b>1. Không nghe thấy tiếng còi khi chai lỗi</b>", styles["TableCellBold"]),
            Paragraph("Chính sách Autoplay của trình duyệt chặn âm thanh tự động khi chưa có tương tác.", styles["TableCell"]),
            Paragraph("Nhấp chuột vào một vị trí bất kỳ trên trang web để cấp quyền Web Audio; kiểm tra công tắc âm thanh bên cạnh bảng số liệu.", styles["TableCell"])
        ],
        [
            Paragraph("<b>2. Video bị giật hình hoặc FPS thấp (&lt; 15 FPS)</b>", styles["TableCellBold"]),
            Paragraph("Đang để độ phân giải 640px trên máy tính văn phòng chỉ dùng CPU.", styles["TableCell"]),
            Paragraph("Tại thanh điều khiển, đổi mục 'Độ phân giải suy luận' sang <b>'⚡ 480px (Siêu mượt)'</b>. FPS sẽ tăng ngay lên 22–25 FPS.", styles["TableCell"])
        ],
        [
            Paragraph("<b>3. Webcam hiển thị màn hình đen</b>", styles["TableCellBold"]),
            Paragraph("Ứng dụng khác (Zoom, Teams, Camera App) đang chiếm dụng camera.", styles["TableCell"]),
            Paragraph("Đóng các ứng dụng khác, chọn lại nguồn 'Webcam 0' và bấm Bắt đầu kiểm định.", styles["TableCell"])
        ],
        [
            Paragraph("<b>4. Các đồ vật khác bị báo lỗi màu đỏ</b>", styles["TableCellBold"]),
            Paragraph("Đang để chế độ 'QC Chai Chuyên Sâu' trên video tự quay có nhiều tạp vật.", styles["TableCell"]),
            Paragraph("Đổi chế độ kiểm định sang <b>'🍶 Chai &amp; Dị Vật Khác'</b>. Các vật thể khác sẽ được khoanh viền tím và đếm riêng vào mục Dị vật.", styles["TableCell"])
        ],
        [
            Paragraph("<b>5. Tải video mới lên báo lỗi thất bại</b>", styles["TableCellBold"]),
            Paragraph("Dung lượng vượt quá 200MB hoặc đuôi định dạng file không hỗ trợ.", styles["TableCell"]),
            Paragraph("Đảm bảo file có định dạng chuẩn (.mp4, .avi, .mov, .mkv) và dung lượng dưới 200MB.", styles["TableCell"])
        ],
    ]
    t_trouble = Table(trouble_data, colWidths=[4.2 * cm, 4.8 * cm, 8.0 * cm])
    t_trouble.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(t_trouble)

    story.append(Spacer(1, 0.8 * cm))

    # =========================================================================
    # PHẦN PHÊ DUYỆT & NGHIỆM THU TÀI LIỆU VẬN HÀNH
    # =========================================================================
    sign_data = [
        [Paragraph("<b>NGƯỜI BIÊN SOẠN TÀI LIỆU</b>", styles["TableCellBold"]), Paragraph("<b>PHÊ DUYỆT BAN HÀNH QUY TRÌNH HMI</b>", styles["TableCellBold"])],
        [Paragraph("<i>(Ký và ghi rõ họ tên)</i>", styles["TableCell"]), Paragraph("<i>(Ký và ghi rõ họ tên)</i>", styles["TableCell"])],
        [Spacer(1, 1.8 * cm), Spacer(1, 1.8 * cm)],
        [Paragraph("<b>Kỹ sư Trưởng UI/UX &amp; AI</b><br/>Dự án ConveyorVision", styles["TableCellBold"]), Paragraph("<b>Quản Đốc / Trưởng Ca Vận Hành</b><br/>Trạm Kiểm Định Băng Chuyền Tự Động", styles["TableCellBold"])]
    ]
    t_sign = Table(sign_data, colWidths=[8.5 * cm, 8.5 * cm])
    t_sign.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether(t_sign))

    # Xuất file PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(pdf_path)

if __name__ == "__main__":
    out_pdf = build_pdf()
    sys.stdout.buffer.write(f"PDF UI/UX Guide generated: {out_pdf}\n".encode("utf-8"))
