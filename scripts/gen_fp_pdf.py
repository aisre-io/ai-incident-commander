from fpdf import FPDF

class FPPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("SimHei", "", 7)
            self.set_text_color(150,150,150)
            self.cell(0, 5, "AI Incident Commander | Founding Partner Program", align="C", new_x="LMARGIN", new_y="NEXT")
            self.line(10, 12, 200, 12)
            self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("SimHei", "", 7)
        self.set_text_color(180,180,180)
        self.cell(0, 10, f"Confidential  |  Page {self.page_no()}/{{nb}}", align="C")

pdf = FPPDF()
pdf.alias_nb_pages()
pdf.add_page()

fpath = "C:\\Windows\\Fonts\\simhei.ttf"
pdf.add_font("SimHei", "", fpath, uni=True)

DARK = (30, 40, 80)
ACCENT = (70, 100, 200)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
BG = (245, 247, 252)

# --- top accent bar ---
pdf.set_fill_color(*ACCENT)
pdf.rect(0, 0, 210, 4, "F")

# --- hero section ---
pdf.set_fill_color(*DARK)
pdf.rect(0, 4, 210, 38, "F")

pdf.set_y(10)
pdf.set_font("SimHei", "", 22)
pdf.set_text_color(*WHITE)
pdf.cell(0, 10, "AI Incident Commander", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_font("SimHei", "", 12)
pdf.set_text_color(180, 200, 255)
pdf.cell(0, 8, "Founding Partner Program", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_font("SimHei", "", 8)
pdf.set_text_color(160, 180, 220)
pdf.cell(0, 6, "AI-powered Incident Root Cause Analysis  |  MIT Open Source", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(6)

# --- 3 stat cards ---
stats = [
    ("~12 sec", "Time to RCA"),
    ("87.31%", "Accuracy"),
    ("10 types", "Fault coverage"),
]
card_w = 56
gap = 8
start_x = (210 - (card_w * 3 + gap * 2)) / 2

for i, (val, label) in enumerate(stats):
    x = start_x + i * (card_w + gap)
    pdf.set_fill_color(*ACCENT)
    pdf.rect(x, pdf.get_y(), card_w, 20, "F")
    pdf.set_xy(x, pdf.get_y() + 3)
    pdf.set_font("SimHei", "", 14)
    pdf.set_text_color(*WHITE)
    pdf.cell(card_w, 7, val, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(x, pdf.get_y())
    pdf.set_font("SimHei", "", 7)
    pdf.set_text_color(200, 220, 255)
    pdf.cell(card_w, 5, label, align="C")

pdf.ln(12)

# --- body sections ---
sections = [
    ("What is it?", [
        "An AI-powered incident RCA tool. Receive an alert -> auto-correlate Git commits -> output",
        "root cause + fix suggestion in ~12 seconds, 87% accuracy across 10 fault types.",
    ]),
    ("The Problem", [
        "On-call engineers spend 30-60 minutes per incident hunting across logs, metrics, and code.",
        "Alert fatigue is real. We compress diagnosis from an hour to seconds.",
    ]),
    ("Tech Stack", [
        "- DeepSeek V4 Flash (default) + Pro escalation gate",
        "- LangGraph agent orchestration: cluster -> RCA -> synthesis",
        "- Feishu/Lark notification cards, color-coded by severity",
        "- MIT License  |  gitee.com/ai-sre/ai-incident-commander",
    ]),
    ("Founding Partner Program", [
        "Mutual selection. We're selecting 5 partners (not public sign-up).",
        "",
        "We provide:                                     You provide:",
        "  12 months Pro free                             30 min feedback / month",
        "  Founder-direct access                          Anonymous incident data",
        "  Feature prioritization                         Optional: reference letter / VC intro",
        "  Co-authored postmortem",
    ]),
    ("Current Progress", [
        "- 61/61 tests passing, 2.16s runtime",
        "- RCA accuracy: 87.31% (26 samples, 10 fault types, LLM-as-judge)",
        "- Lark full pipeline verified: critical incident cards in Feishu",
        "- Docker ready, deployable in 5 min",
        "- Gitee: 59 files / 6.7K lines / CI enabled",
        "- Day 30 nurture template (v2) ready for overseas follow-up",
    ]),
    ("Contact", [
        "Jacky  |  Founder, AI Incident Commander",
        "gitee.com/ai-sre/ai-incident-commander",
    ]),
]

for title, lines in sections:
    pdf.set_fill_color(*BG)
    pdf.set_font("SimHei", "", 12)
    pdf.set_text_color(*DARK)
    h = 7
    pdf.cell(0, h, f"  {title}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("SimHei", "", 9)
    pdf.set_text_color(*GRAY)
    for line in lines:
        if line == "":
            pdf.ln(1)
            continue
        pdf.cell(0, 5.5, f"  {line}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

# --- bottom accent bar ---
pdf.set_fill_color(*ACCENT)
pdf.rect(0, 292, 210, 5, "F")

out = "D:\\Jacky\\AI-Native DevOps\\ai-incident-commander\\outreach\\AI_Incident_Commander_FP_Program.pdf"
pdf.output(out)
print(f"OK: {out}")
