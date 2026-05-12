"""
utils/pdf_exporter.py
=====================
Generates a formatted PDF report for a completed legal case using ReportLab.

Sections: Cover · Case Description · Research · Debate Rounds · Defense ·
Prosecution · Judge · Appeals
"""

import json
import re
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#0e0d0b")
GOLD = colors.HexColor("#b8902a")
GOLD_LIGHT = colors.HexColor("#e8d49a")
PARCHMENT = colors.HexColor("#f5f0e8")
GREEN = colors.HexColor("#1a6640")
RED = colors.HexColor("#8b1a1a")
LGRAY = colors.HexColor("#e8e2d8")


def S(name, **kw):
    return ParagraphStyle(name, **kw)


STYLES = {
    "cover_title": S("ct", fontName="Times-BoldItalic", fontSize=32, leading=38, textColor=INK, alignment=TA_CENTER, spaceAfter=8),
    "cover_sub": S("cs", fontName="Courier", fontSize=9, textColor=GOLD, alignment=TA_CENTER, spaceAfter=4),
    "agent_label": S("al", fontName="Courier-Bold", fontSize=7.5, textColor=GOLD, spaceAfter=6),
    "body": S("bd", fontName="Times-Roman", fontSize=10.5, leading=17, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "bullet": S("bu", fontName="Times-Roman", fontSize=10.5, leading=17, textColor=INK, leftIndent=14, spaceAfter=5),
    "metric_label": S("ml", fontName="Courier", fontSize=7, textColor=LGRAY, alignment=TA_CENTER, spaceAfter=2),
    "metric_value": S("mv", fontName="Times-Bold", fontSize=16, alignment=TA_CENTER, spaceAfter=4),
}


def _ruling_color(ruling: str):
    lowered = (ruling or "").lower()
    if "not" in lowered or "insufficient" in lowered:
        return GREEN
    if "guilty" in lowered or "liable" in lowered:
        return RED
    return colors.HexColor("#7a5f1a")


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, height - 1.5 * cm, width - 2 * cm, height - 1.5 * cm)
    canvas.setFont("Courier", 7)
    canvas.setFillColor(GOLD)
    canvas.drawCentredString(width / 2, height - 1.2 * cm, "LEXAI - MULTI-AGENT LEGAL REASONING SYSTEM")
    canvas.setStrokeColor(LGRAY)
    canvas.line(2 * cm, 1.8 * cm, width - 2 * cm, 1.8 * cm)
    canvas.setFont("Courier", 7)
    canvas.setFillColor(colors.HexColor("#9a8a72"))
    canvas.drawCentredString(width / 2, 1.2 * cm, f"Page {doc.page}")
    canvas.drawCentredString(width / 2, 0.8 * cm, "NOT LEGAL ADVICE - DEMONSTRATION PURPOSES ONLY")
    canvas.restoreState()


def _rich_text(text: str) -> str:
    return escape(str(text or "")).replace("\n", "<br/>")


def _bullets(story, text: str):
    for line in str(text or "").split("\n"):
        clean = re.sub(r"^[•\-\*·§]\s*", "", line.strip())
        if clean:
            story.append(Paragraph(f"Section  { _rich_text(clean) }", STYLES["bullet"]))


def _parse_json(value: str, default):
    try:
        return json.loads(value)
    except Exception:
        return default


def generate_case_pdf(case, agent_outputs: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=f"LexAI - {str(case.title)[:60]}",
        author="LexAI Multi-Agent System",
    )
    story = []

    story += [
        Spacer(1, 2 * cm),
        Paragraph("LexAI", STYLES["cover_title"]),
        Paragraph("MULTI-AGENT LEGAL REASONING REPORT", STYLES["cover_sub"]),
        Spacer(1, 0.4 * cm),
        HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=10),
        Spacer(1, 0.6 * cm),
        Paragraph(f"<font name='Times-BoldItalic' size='14'>{_rich_text(case.title)}</font>", STYLES["body"]),
        Spacer(1, 0.3 * cm),
    ]

    meta = Table(
        [
            ["Case ID", case.id],
            ["Generated", datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")],
            ["Pipeline", "Research -> Debate Rounds -> Scoring -> Judge -> Appeals"],
        ],
        colWidths=[3.5 * cm, 13 * cm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Courier-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (0, -1), GOLD),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#6b5e4a")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PARCHMENT, colors.white]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 0.8 * cm))

    if case.ruling:
        ruling_color = _ruling_color(case.ruling)
        verdict_summary = Table(
            [
                [
                    Paragraph("<font size='7' color='#9a8a72'>RULING</font>", STYLES["metric_label"]),
                    Paragraph("<font size='7' color='#9a8a72'>CONFIDENCE</font>", STYLES["metric_label"]),
                ],
                [
                    Paragraph(f"<font color='{ruling_color.hexval()}'><b>{_rich_text(case.ruling)}</b></font>", STYLES["metric_value"]),
                    Paragraph(f"<b>{int(case.confidence or 0)}%</b>", STYLES["metric_value"]),
                ],
            ],
            colWidths=[8.25 * cm, 8.25 * cm],
        )
        verdict_summary.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PARCHMENT),
                    ("BOX", (0, 0), (-1, -1), 0.5, GOLD_LIGHT),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, GOLD_LIGHT),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(verdict_summary)

    story.append(PageBreak())

    story += [
        Paragraph("CASE DESCRIPTION", STYLES["agent_label"]),
        HRFlowable(width="100%", thickness=0.5, color=GOLD_LIGHT, spaceAfter=8),
        Paragraph(_rich_text(case.case_description), STYLES["body"]),
        Spacer(1, 0.5 * cm),
    ]

    if "research" in agent_outputs:
        story += [
            Paragraph("RESEARCH AGENT - LEGAL DOCTRINE AND CONTEXT", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=GOLD_LIGHT, spaceAfter=8),
        ]
        _bullets(story, agent_outputs["research"])
        story.append(Spacer(1, 0.5 * cm))

    if "rounds" in agent_outputs:
        rounds = _parse_json(agent_outputs["rounds"], [])
        if rounds:
            story += [
                Paragraph("DEBATE ROUNDS - SAME TIMELINE AS THE RESULTS VIEW", STYLES["agent_label"]),
                HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#6a86b8"), spaceAfter=8),
            ]
            for item in rounds:
                label = item.get("label") or f"Round {item.get('round', '?')}"
                story.append(Paragraph(f"<b>{_rich_text(label)}</b>", STYLES["body"]))
                story.append(Paragraph(f"<b>Defense</b><br/>{_rich_text(item.get('defense', ''))}", STYLES["body"]))
                story.append(Paragraph(f"<b>Prosecution</b><br/>{_rich_text(item.get('prosecution', ''))}", STYLES["body"]))
                story.append(Spacer(1, 0.25 * cm))
            story.append(Spacer(1, 0.4 * cm))

    if "defense" in agent_outputs:
        story += [
            Paragraph("DEFENSE AGENT - MERGED ARGUMENT SET", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#4caf7d"), spaceAfter=8),
        ]
        _bullets(story, agent_outputs["defense"])
        story.append(Spacer(1, 0.5 * cm))

    if "prosecution" in agent_outputs:
        story += [
            Paragraph("PROSECUTION AGENT - MERGED ARGUMENT SET", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c04040"), spaceAfter=8),
        ]
        _bullets(story, agent_outputs["prosecution"])
        story.append(Spacer(1, 0.5 * cm))

    if "evidence" in agent_outputs:
        evidence = _parse_json(agent_outputs["evidence"], {})
        story += [
            Paragraph("EVIDENCE VIEWER - RETRIEVED LEGAL SOURCES", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=GOLD_LIGHT, spaceAfter=8),
        ]
        for item in (evidence.get("documents") or [])[:6]:
            title = item.get("title") or item.get("citation") or "Untitled Source"
            citation = item.get("citation") or "No citation"
            content = item.get("content") or ""
            story.append(Paragraph(f"<b>{_rich_text(title)}</b> - {_rich_text(citation)}", STYLES["body"]))
            story.append(Paragraph(_rich_text(content), STYLES["body"]))
            story.append(Spacer(1, 0.18 * cm))
        story.append(Spacer(1, 0.4 * cm))

    if "scoring" in agent_outputs:
        scoring = _parse_json(agent_outputs["scoring"], {})
        story += [
            Paragraph("ARGUMENT STRENGTH METRICS", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#6a86b8"), spaceAfter=8),
        ]
        story.append(
            Paragraph(
                f"<b>Defense Score:</b> {int(scoring.get('defense_score', 0))}%<br/>"
                f"<b>Prosecution Score:</b> {int(scoring.get('prosecution_score', 0))}%<br/>"
                f"<b>Stronger Side:</b> {_rich_text(scoring.get('stronger_side', 'balanced'))}",
                STYLES["body"],
            )
        )
        if scoring.get("explanation"):
            story.append(Paragraph(_rich_text(scoring["explanation"]), STYLES["body"]))
        story.append(Spacer(1, 0.5 * cm))

    if "judge" in agent_outputs:
        verdict = _parse_json(agent_outputs["judge"], {})
        story += [
            Paragraph("JUDGE AGENT - VERDICT AND REASONING", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#7b5ea7"), spaceAfter=8),
        ]
        if verdict.get("reasoning"):
            story.append(Paragraph(_rich_text(verdict["reasoning"]), STYLES["body"]))
        if verdict.get("key_finding"):
            story.append(Paragraph(f"<b>Key Finding:</b> {_rich_text(verdict['key_finding'])}", STYLES["body"]))
        story.append(Spacer(1, 0.5 * cm))

    if "appeals" in agent_outputs:
        appeal = _parse_json(agent_outputs["appeals"], {})
        story.append(PageBreak())
        story += [
            Paragraph("APPEALS AGENT - APPELLATE REVIEW", STYLES["agent_label"]),
            HRFlowable(width="100%", thickness=0.5, color=GOLD_LIGHT, spaceAfter=8),
        ]
        story.append(Paragraph(f"<b>Appeal Warranted:</b> {'Yes' if appeal.get('appeal_warranted') else 'No'}", STYLES["body"]))
        story.append(Paragraph(f"<b>Recommended Action:</b> {_rich_text(appeal.get('recommended_action', '-'))}", STYLES["body"]))
        story.append(Paragraph(f"<b>Appeal Strength:</b> {appeal.get('appeal_strength', 0)}%", STYLES["body"]))
        for ground in appeal.get("grounds", []):
            story.append(Paragraph(f"Section  {_rich_text(ground)}", STYLES["bullet"]))
        if appeal.get("dissenting_view"):
            story.append(Paragraph(f"<b>Dissenting View:</b> {_rich_text(appeal['dissenting_view'])}", STYLES["body"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buf.seek(0)
    return buf.read()
