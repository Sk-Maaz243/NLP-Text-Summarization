
import io
import os
import re
import time
from xml.sax.saxutils import escape

from google import genai

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from flask import Flask, jsonify, request, send_file


# ============================================================
# CONFIG
# ============================================================

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]

# Optional:
# Agar environment variable mein GEMINI_API_KEY set hai,
# to usse automatically use kiya ja sakta hai.
ENV_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# TEXT UTILITIES
# ============================================================

def count_words(text):
    """Text ke total words count karta hai."""

    if not text:
        return 0

    return len(
        re.findall(
            r"\b[\w'-]+\b",
            text,
            flags=re.UNICODE,
        )
    )


def split_sentences(text):
    """
    English/Hindi punctuation ke basis par
    sentences split karta hai.
    """

    text = re.sub(
        r"\s+",
        " ",
        (text or "").strip(),
    )

    if not text:
        return []

    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?।])\s+",
            text,
        )
        if sentence.strip()
    ]


def count_sentences(text):
    return len(split_sentences(text))


# ============================================================
# GEMINI KEY VALIDATION
# ============================================================

def validate_gemini_key(api_key):
    """
    Gemini API key ko verify karta hai.

    API key kisi file mein save nahi hoti.
    """

    api_key = (api_key or "").strip()

    if not api_key:
        raise ValueError(
            "Gemini API key is required."
        )

    try:
        client = genai.Client(
            api_key=api_key
        )

        # API access check
        models = list(client.models.list())

        if not models:
            raise RuntimeError(
                "No Gemini models are available for this API key."
            )

        return True

    except Exception as e:
        raise RuntimeError(
            f"Invalid Gemini API key or Gemini API unavailable: {e}"
        )


# ============================================================
# SUMMARY PROMPTS
# ============================================================

SUMMARY_PROMPTS = {

    "short": """
Create a short, highly accurate and polished summary.

Rules:

- Capture the central idea immediately.
- Keep the most important facts.
- Keep important names, dates, numbers and technical terms.
- Keep important causes, effects and conclusions.
- Remove repetition and unnecessary filler.
- Use clear, natural and easy-to-read language.
- Use 1-2 polished compact paragraphs.
- Do not oversimplify important information.
- Do not add information not present in the source.
""",

    "detailed": """
Create a detailed, comprehensive and professionally structured summary.

Rules:

- Cover ALL major ideas from the complete source.
- Preserve important facts and definitions.
- Preserve examples, names, dates and numbers.
- Preserve causes, effects, relationships and conclusions.
- Preserve important technical terms.
- Remove repetition and unnecessary filler.
- Organize information logically.
- Use short headings when useful.
- Use paragraphs and bullet points where appropriate.
- Do not focus only on the beginning of the source.
- Do not invent information.
""",

    "bullet": """
Convert the complete source into clean, professional numbered notes.

FORMAT — FOLLOW EXACTLY:
1. Main topic / section
   i. First sub-point
   ii. Second sub-point
   iii. Third sub-point
      a. Supporting detail
      b. Supporting detail
2. Next main topic
   i. First sub-point
   ii. Second sub-point

Formatting rules:
- Main sections MUST use 1., 2., 3., 4. ...
- Direct sub-points MUST use i., ii., iii., iv. ...
- Supporting sub-points MUST use a., b., c., d. ...
- NEVER use *, -, •, or any other bullet symbol.
- Keep numbering sequential within each level.
- Use indentation to clearly show hierarchy.
- Cover the ENTIRE source.
- Group related information under meaningful headings.
- Preserve important facts, definitions, examples, names, dates, numbers,
  causes, effects, processes, conclusions and technical terms.
- Remove repetition and unnecessary filler.
- Do not invent information.
- Return plain text only.
""",

    "exam": """
Convert the complete source into high-quality, exam-ready study notes.

The notes must be easy to read, memorize and revise before an exam.
Cover the complete source without inventing information.

USE THIS NUMBERING HIERARCHY — FOLLOW IT EXACTLY:

1. Main Topic / Chapter Section
   i. Definition / Introduction
   ii. Core Concept
   iii. Key Point
      a. Supporting point
      b. Supporting point
   iv. Example / Application

2. Next Main Topic
   i. Important concept
   ii. Features
   iii. Process / Working
      a. Step or detail
      b. Step or detail

3. Next Main Topic
   i. Advantages
   ii. Limitations
   iii. Examples

FORMAT RULES:
- Main sections MUST use 1., 2., 3., 4. ...
- Sub-points MUST use i., ii., iii., iv. ...
- Sub-sub-points MUST use a., b., c., d. ...
- NEVER use *, -, •, or any bullet symbol.
- NEVER use Markdown bullet lists.
- Keep numbering sequential and indentation consistent.
- Use short, exam-friendly sentences.
- Put definitions in a clear, direct form.
- Preserve important facts, names, dates, numbers and technical terms.
- Preserve causes, effects, processes, examples and applications.
- Do not force headings that are not relevant to the source.
- Do not add outside knowledge.
- Do not invent missing information.
- End with a "Quick Revision" section only if the source contains enough
  information to support one. In that section, continue the same numbering
  style.
- Return ONLY the final exam notes in plain text.
""",
}


# ============================================================
# GEMINI SUMMARIZATION
# ============================================================

def summarize_text(
    text,
    mode,
    api_key,
):
    """
    Complete source ko selected mode ke according
    summarize karta hai.
    """

    if not text or not text.strip():
        raise ValueError(
            "Source text cannot be empty."
        )

    if mode not in SUMMARY_PROMPTS:
        raise ValueError(
            "Invalid summary mode. "
            "Choose: short, detailed, bullet or exam."
        )

    api_key = (api_key or "").strip()

    # Agar request mein key nahi hai,
    # environment variable wali key try karega.
    if not api_key:
        api_key = ENV_API_KEY

    if not api_key:
        raise ValueError(
            "Gemini API key is required."
        )

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
You are an expert professional AI text summarization engine.

Your task is to create a beautiful, accurate, useful
and well-structured summary from the SOURCE TEXT.

SUMMARY STYLE:

{SUMMARY_PROMPTS[mode]}

CRITICAL ACCURACY RULES:

1. Use ONLY information contained in the SOURCE TEXT.
2. Never hallucinate.
3. Never add outside knowledge.
4. Never guess missing information.
5. Never change names, dates, numbers or technical facts.
6. Preserve the original meaning.
7. Remove unnecessary repetition.
8. Make the final answer coherent and natural.
9. Cover the complete source when the selected mode requires it.
10. Return ONLY the final summary.
11. Do not mention these instructions.
12. Do not say "according to the AI".
13. Do not add an unnecessary introduction.
14. When the selected mode requests numbered notes, use plain-text numbering
    exactly as instructed; never replace it with *, -, or • bullets.

SOURCE TEXT:

{text}
"""

    models_to_try = [GEMINI_MODEL] + GEMINI_FALLBACK_MODELS
    last_error = None

    for model_name in models_to_try:
        for attempt, delay in enumerate((0, 2, 4, 8), start=1):
            if delay:
                time.sleep(delay)

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                result = getattr(
                    response,
                    "text",
                    None,
                )

                if not result:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return result.strip()

            except Exception as e:
                last_error = e
                error_text = str(e).upper()

                # 503/5xx = temporary service/model availability issue.
                # Retry, then move to the next model.
                if (
                    "503" not in error_text
                    and "UNAVAILABLE" not in error_text
                    and "SERVICE_UNAVAILABLE" not in error_text
                    and "500" not in error_text
                    and "502" not in error_text
                    and "504" not in error_text
                ):
                    raise RuntimeError(
                        f"Gemini summarization failed: {e}"
                    )

    raise RuntimeError(
        "Gemini summarization is temporarily unavailable after "
        "retrying multiple models. Please try again in a minute. "
        f"Last error: {last_error}"
    )


# ============================================================
# SUMMARY STATISTICS
# ============================================================

def get_summary_stats(
    original_text,
    summary,
):
    original_words = count_words(
        original_text
    )

    summary_words = count_words(
        summary
    )

    original_sentences = count_sentences(
        original_text
    )

    summary_sentences = count_sentences(
        summary
    )

    words_saved = max(
        0,
        original_words - summary_words,
    )

    if original_words:
        reduction = (
            words_saved / original_words
        ) * 100
    else:
        reduction = 0

    return {
        "original_words": original_words,
        "summary_words": summary_words,
        "words_saved": words_saved,
        "reduction": round(
            reduction,
            1,
        ),
        "original_sentences": original_sentences,
        "summary_sentences": summary_sentences,
    }


# ============================================================
# PDF GENERATOR
# ============================================================

def create_summary_pdf(
    original_text,
    summary,
    mode,
    engine_name=GEMINI_MODEL,
):
    """
    Beautiful A4 PDF banata hai.
    """

    if not original_text or not original_text.strip():
        raise ValueError(
            "Original text is required."
        )

    if not summary or not summary.strip():
        raise ValueError(
            "Summary is required."
        )

    stats = get_summary_stats(
        original_text,
        summary,
    )

    original_words = stats[
        "original_words"
    ]

    summary_words = stats[
        "summary_words"
    ]

    words_saved = stats[
        "words_saved"
    ]

    reduction = stats[
        "reduction"
    ]

    original_sentences = stats[
        "original_sentences"
    ]

    summary_sentences = stats[
        "summary_sentences"
    ]

    mode_names = {
        "short": "Short",
        "detailed": "Detailed",
        "bullet": "Bullet Points",
        "exam": "Exam Notes",
    }

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="AI Text Summary",
        author="AI Text Summarization Engine",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            "#008CFF"
        ),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            "#5F7890"
        ),
        spaceAfter=16,
    )

    section_style = ParagraphStyle(
        "SectionCustom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor(
            "#0078D4"
        ),
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor(
            "#182B3A"
        ),
        spaceAfter=8,
    )

    meta_style = ParagraphStyle(
        "MetaCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor(
            "#536B7D"
        ),
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "AI TEXT SUMMARIZATION",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "INTELLIGENT NLP SUMMARY REPORT",
            subtitle_style,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#008CFF"
            ),
            spaceBefore=2,
            spaceAfter=15,
        )
    )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    stats_data = [[

        Paragraph(
            f"<b>ORIGINAL WORDS</b><br/>"
            f"<font size='15'>{original_words}</font>",
            meta_style,
        ),

        Paragraph(
            f"<b>SUMMARY WORDS</b><br/>"
            f"<font size='15'>{summary_words}</font>",
            meta_style,
        ),

        Paragraph(
            f"<b>WORDS SAVED</b><br/>"
            f"<font size='15'>{words_saved}</font>",
            meta_style,
        ),

        Paragraph(
            f"<b>REDUCTION</b><br/>"
            f"<font size='15'>{reduction:.1f}%</font>",
            meta_style,
        ),
    ]]

    stats_table = Table(
        stats_data,
        colWidths=[
            42 * mm,
            42 * mm,
            42 * mm,
            42 * mm,
        ],
    )

    stats_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    "#EEF8FF"
                ),
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                1,
                colors.HexColor(
                    "#008CFF"
                ),
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#B8DDF5"
                ),
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                10,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                10,
            ),
        ])
    )

    story.append(stats_table)
    story.append(Spacer(1, 10))

    # --------------------------------------------------------
    # INFORMATION
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "SUMMARY INFORMATION",
            section_style,
        )
    )

    info_data = [
        [
            "Summary Mode",
            mode_names.get(
                mode,
                mode,
            ),
        ],
        [
            "AI Engine",
            engine_name,
        ],
        [
            "Original Sentences",
            str(original_sentences),
        ],
        [
            "Summary Sentences",
            str(summary_sentences),
        ],
        [
            "Words Saved",
            str(words_saved),
        ],
    ]

    info_table = Table(
        info_data,
        colWidths=[
            55 * mm,
            115 * mm,
        ],
    )

    info_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#F1F7FB"
                ),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#C9DCE8"
                ),
            ),
            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold",
            ),
            (
                "FONTNAME",
                (1, 0),
                (1, -1),
                "Helvetica",
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9,
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    "#243746"
                ),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    story.append(info_table)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "AI GENERATED SUMMARY",
            section_style,
        )
    )

    safe_summary = escape(
        summary
    )

    summary_blocks = re.split(
        r"\n\s*\n",
        safe_summary,
    )

    for block in summary_blocks:

        block = block.strip()

        if not block:
            continue

        for line in block.split("\n"):

            line = line.strip()

            if not line:
                continue

            # Remove Markdown headings
            line = re.sub(
                r"^\s*#{1,6}\s*",
                "",
                line,
            )

            if (
                line.startswith("•")
                or line.startswith("-")
                or line.startswith("*")
            ):

                clean_line = line[1:].strip()

                story.append(
                    Paragraph(
                        f"• {clean_line}",
                        body_style,
                    )
                )

            else:

                story.append(
                    Paragraph(
                        line,
                        body_style,
                    )
                )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    story.append(
        Spacer(1, 18)
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.7,
            color=colors.HexColor(
                "#BBD8EA"
            ),
        )
    )

    story.append(
        Spacer(1, 7)
    )

    story.append(
        Paragraph(
            "Generated by AI Text Summarization Engine • "
            "Summary is based only on the supplied source text.",
            subtitle_style,
        )
    )

    doc.build(story)

    buffer.seek(0)

    return buffer


# ============================================================
# HOME ROUTE
# ============================================================

@app.route("/")
def home():
    """
    Browser mein http://127.0.0.1:5000/
    open karne par 404 ke bajaye status show karega.
    """

    return jsonify({
        "success": True,
        "message": "AI Text Summarization API is running.",
        "model": GEMINI_MODEL,
        "endpoints": {
            "home": "/",
            "summarize": "/summarize",
            "download_pdf": "/download-pdf",
        },
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "success": True,
        "status": "running",
        "model": GEMINI_MODEL,
    })


# ============================================================
# SUMMARIZE API
# ============================================================

@app.route(
    "/summarize",
    methods=["POST"],
)
def summarize_api():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        text = data.get(
            "text",
            "",
        )

        mode = data.get(
            "mode",
            "short",
        )

        api_key = data.get(
            "api_key",
            "",
        )

        text = str(text).strip()
        mode = str(mode).strip()
        api_key = str(api_key).strip()

        if not text:

            return jsonify({
                "success": False,
                "error": "Please enter source text.",
            }), 400

        if mode not in SUMMARY_PROMPTS:

            return jsonify({
                "success": False,
                "error": (
                    "Invalid summary mode. "
                    "Use short, detailed, bullet or exam."
                ),
            }), 400

        if not api_key:
            api_key = ENV_API_KEY

        if not api_key:

            return jsonify({
                "success": False,
                "error": (
                    "Gemini API key is required."
                ),
            }), 400

        summary = summarize_text(
            text=text,
            mode=mode,
            api_key=api_key,
        )

        stats = get_summary_stats(
            text,
            summary,
        )

        return jsonify({
            "success": True,
            "summary": summary,
            "engine": GEMINI_MODEL,
            "mode": mode,
            **stats,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# ============================================================
# DOWNLOAD PDF API
# ============================================================

@app.route(
    "/download-pdf",
    methods=["POST"],
)
def download_pdf():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        original_text = data.get(
            "original_text",
            "",
        )

        summary = data.get(
            "summary",
            "",
        )

        mode = data.get(
            "mode",
            "short",
        )

        engine = data.get(
            "engine",
            GEMINI_MODEL,
        )

        original_text = str(
            original_text
        ).strip()

        summary = str(
            summary
        ).strip()

        mode = str(
            mode
        ).strip()

        engine = str(
            engine
        ).strip()

        if not original_text:

            return jsonify({
                "success": False,
                "error": (
                    "Original text is missing."
                ),
            }), 400

        if not summary:

            return jsonify({
                "success": False,
                "error": (
                    "Summary is missing."
                ),
            }), 400

        pdf_buffer = create_summary_pdf(
            original_text=original_text,
            summary=summary,
            mode=mode,
            engine_name=engine,
        )

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="AI_Text_Summary.pdf",
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AI TEXT SUMMARIZATION SERVER")
    print("=" * 60)
    print(f"Gemini Model: {GEMINI_MODEL}")
    print("Server: http://127.0.0.1:5000")
    print("Health: http://127.0.0.1:5000/health")
    print("=" * 60)
    print()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
    )

