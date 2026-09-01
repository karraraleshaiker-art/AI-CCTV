from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "factory_workforce_ai_cctv_proposal.pdf"


class RoadmapFlow(Flowable):
    def __init__(self) -> None:
        super().__init__()
        self.width = 170 * mm
        self.height = 34 * mm

    def draw(self) -> None:
        labels = [
            ("1", "Workforce\nSystem"),
            ("2", "Requests and\nApprovals"),
            ("3", "Attendance\nFoundation"),
            ("4", "AI CCTV\nIntegration"),
        ]
        box_w = 37 * mm
        gap = 6 * mm
        y = 4 * mm
        for index, (number, label) in enumerate(labels):
            x = index * (box_w + gap)
            self.canv.setFillColor(colors.HexColor("#F6F8FA"))
            self.canv.setStrokeColor(colors.HexColor("#9AA7B2"))
            self.canv.roundRect(x, y, box_w, 22 * mm, 4, fill=1, stroke=1)
            self.canv.setFillColor(colors.HexColor("#1D4E89"))
            self.canv.circle(x + 6 * mm, y + 16 * mm, 4 * mm, fill=1, stroke=0)
            self.canv.setFillColor(colors.white)
            self.canv.setFont("Helvetica-Bold", 8)
            self.canv.drawCentredString(x + 6 * mm, y + 14.8 * mm, number)
            self.canv.setFillColor(colors.HexColor("#17212B"))
            self.canv.setFont("Helvetica-Bold", 8.5)
            for line_number, text in enumerate(label.split("\n")):
                self.canv.drawString(x + 12 * mm, y + (16 - line_number * 4.4) * mm, text)
            if index < len(labels) - 1:
                start_x = x + box_w + 1 * mm
                end_x = x + box_w + gap - 1 * mm
                arrow_y = y + 11 * mm
                self.canv.setStrokeColor(colors.HexColor("#6B7785"))
                self.canv.line(start_x, arrow_y, end_x, arrow_y)
                self.canv.line(end_x, arrow_y, end_x - 2 * mm, arrow_y + 1.5 * mm)
                self.canv.line(end_x, arrow_y, end_x - 2 * mm, arrow_y - 1.5 * mm)


def build_pdf() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Workforce Management Foundation Before AI CCTV",
        author="AI CCTV Project",
    )
    styles = make_styles()
    story = []

    story.extend(cover_page(styles))
    story.append(PageBreak())
    story.extend(proposal_body(styles))
    story.append(PageBreak())
    story.extend(implementation_page(styles))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return OUTPUT_PATH


def cover_page(styles: dict[str, ParagraphStyle]) -> list:
    return [
        Spacer(1, 20 * mm),
        Paragraph("Proposal", styles["eyebrow"]),
        Paragraph("Build a Workforce Management Foundation Before AI CCTV", styles["title"]),
        Spacer(1, 8 * mm),
        Paragraph(
            "A step-by-step approach for introducing AI camera monitoring in the factory without creating confusion, "
            "unfair alerts, or unnecessary privacy concerns.",
            styles["subtitle"],
        ),
        Spacer(1, 18 * mm),
        RoadmapFlow(),
        Spacer(1, 20 * mm),
        callout(
            "Recommendation",
            "Do not cancel the AI CCTV vision. Pause the camera monitoring rollout and first build a simple digital "
            "workforce system for employees, shifts, requests, approvals, and leave planning. This creates the data "
            "foundation the AI system needs to work correctly later.",
            styles,
        ),
    ]


def proposal_body(styles: dict[str, ParagraphStyle]) -> list:
    return [
        section_title("1. Current Situation", styles),
        Paragraph(
            "The AI CCTV system is intended to monitor assigned work zones and detect events such as phone use or a "
            "person leaving a specific place. While the technical idea is possible, the system needs reliable context "
            "before it can make fair decisions.",
            styles["body"],
        ),
        Paragraph(
            "For example, if a person is assigned to a zone during the morning shift, but later changes shifts or "
            "temporarily exchanges places with another employee, the AI camera alone cannot know whether this is a "
            "violation or an approved change.",
            styles["body"],
        ),
        Spacer(1, 4 * mm),
        problem_table(styles),
        Spacer(1, 7 * mm),
        section_title("2. Why A Management System Should Come First", styles),
        Paragraph(
            "Before AI monitoring can be reliable, the factory should have a digital record of who is working, which "
            "shift they belong to, where they are assigned, and which changes have been approved. Without this, the "
            "AI system may create false alerts and managers will still need to manually investigate every case.",
            styles["body"],
        ),
        bullet_list(
            [
                "Employee records become organized without asking for biometrics at the beginning.",
                "Shift assignment becomes clear for morning and night teams.",
                "Shift swaps can be requested by one employee, accepted by the other, and approved by a manager.",
                "Leave and holiday requests can be checked against available balances and production needs.",
                "The future AI CCTV module can use approved schedules instead of guessing.",
            ],
            styles,
        ),
        Spacer(1, 4 * mm),
        callout(
            "Key Point",
            "The AI camera should not be the first system employees experience. The first system should help employees "
            "and managers. Later, camera AI can be added as a safety and compliance layer connected to the same records.",
            styles,
        ),
    ]


def implementation_page(styles: dict[str, ParagraphStyle]) -> list:
    return [
        section_title("3. Proposed First Phase: Factory Workforce Portal", styles),
        Paragraph(
            "The first phase should be a practical portal that replaces paper-based HR and daily workforce requests. "
            "Employees can use a mobile-friendly page, while managers use a dashboard on a laptop.",
            styles["body"],
        ),
        feature_table(styles),
        Spacer(1, 7 * mm),
        section_title("4. Future AI CCTV Integration", styles),
        Paragraph(
            "After the workforce portal is stable, the AI CCTV module can be connected to real shift and assignment "
            "data. This makes alerts more accurate because the system will know who is expected in each zone and when.",
            styles["body"],
        ),
        bullet_list(
            [
                "Zone monitoring can compare camera events with approved assignments.",
                "Shift changes will not create false alerts because approved swaps are already recorded.",
                "Managers can review AI alerts beside shift, leave, and approval history.",
                "The factory can introduce AI gradually with better trust and less resistance.",
            ],
            styles,
        ),
        Spacer(1, 6 * mm),
        section_title("5. Decision Requested", styles),
        callout(
            "Suggested Direction",
            "Approve a step-by-step implementation: first build the workforce management portal, then improve it with "
            "attendance features, and finally integrate AI CCTV after the operational data is ready.",
            styles,
        ),
    ]


def problem_table(styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [
            Paragraph("Issue", styles["table_header"]),
            Paragraph("If We Start With AI CCTV Now", styles["table_header"]),
            Paragraph("If We Start With Workforce Portal", styles["table_header"]),
        ],
        [
            Paragraph("Shift changes", styles["table_cell_bold"]),
            Paragraph("Camera cannot know if a person changed from morning to night shift.", styles["table_cell"]),
            Paragraph("Approved shift changes are recorded before AI uses them.", styles["table_cell"]),
        ],
        [
            Paragraph("Zone assignments", styles["table_cell_bold"]),
            Paragraph("AI may flag the wrong person or a valid replacement.", styles["table_cell"]),
            Paragraph("Each zone can be linked to the correct worker and time.", styles["table_cell"]),
        ],
        [
            Paragraph("Employee trust", styles["table_cell_bold"]),
            Paragraph("Employees may see the project as surveillance first.", styles["table_cell"]),
            Paragraph("Employees first receive a tool that helps requests and approvals.", styles["table_cell"]),
        ],
    ]
    table = Table(data, colWidths=[36 * mm, 64 * mm, 64 * mm])
    table.setStyle(base_table_style())
    return table


def feature_table(styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [Paragraph("Module", styles["table_header"]), Paragraph("Purpose", styles["table_header"])],
        [Paragraph("Employee database", styles["table_cell_bold"]), Paragraph("Names, departments, roles, shift type, leave balance, and manager relation.", styles["table_cell"])],
        [Paragraph("Shift management", styles["table_cell_bold"]), Paragraph("Morning and night shift assignment, schedule visibility, and approved changes.", styles["table_cell"])],
        [Paragraph("Shift swap workflow", styles["table_cell_bold"]), Paragraph("Employee requests a swap, the second employee agrees, then the manager approves.", styles["table_cell"])],
        [Paragraph("Leave and holiday planning", styles["table_cell_bold"]), Paragraph("Employees request dates, the system checks balance and conflicts, managers approve.", styles["table_cell"])],
        [Paragraph("Rest hour requests", styles["table_cell_bold"]), Paragraph("Employees request short rest time digitally instead of using paper or verbal approvals.", styles["table_cell"])],
        [Paragraph("Manager dashboard", styles["table_cell_bold"]), Paragraph("Managers see pending requests, daily staffing, upcoming absences, and reports.", styles["table_cell"])],
    ]
    table = Table(data, colWidths=[48 * mm, 116 * mm])
    table.setStyle(base_table_style())
    return table


def callout(title: str, text: str, styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph(title, styles["callout_title"]), Paragraph(text, styles["callout_body"])]]
    table = Table(data, colWidths=[38 * mm, 126 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF4FB")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#8DB7DB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def bullet_list(items: list[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["body"]), leftIndent=10) for item in items],
        bulletType="bullet",
        leftIndent=14,
        bulletFontName="Helvetica-Bold",
        bulletFontSize=7,
        bulletColor=colors.HexColor("#1D4E89"),
    )


def section_title(text: str, styles: dict[str, ParagraphStyle]) -> KeepTogether:
    return KeepTogether([Spacer(1, 3 * mm), Paragraph(text, styles["section"])])


def base_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4E89")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CAD2DB")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FBFCFD")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "Eyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#1D4E89"),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=31,
            textColor=colors.HexColor("#17212B"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12.2,
            leading=18,
            textColor=colors.HexColor("#4C5967"),
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#17212B"),
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.1,
            leading=15.2,
            textColor=colors.HexColor("#26313D"),
            spaceAfter=7,
            alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=10.5,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=11.2,
            textColor=colors.HexColor("#26313D"),
        ),
        "table_cell_bold": ParagraphStyle(
            "TableCellBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.4,
            leading=11.2,
            textColor=colors.HexColor("#17212B"),
        ),
        "callout_title": ParagraphStyle(
            "CalloutTitle",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1D4E89"),
        ),
        "callout_body": ParagraphStyle(
            "CalloutBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.2,
            textColor=colors.HexColor("#26313D"),
        ),
    }


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D8DEE6"))
    canvas.line(20 * mm, 13 * mm, width - 20 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6B7785"))
    canvas.drawString(20 * mm, 8 * mm, "Factory Workforce Management and AI CCTV Roadmap")
    canvas.drawRightString(width - 20 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    print(build_pdf())

