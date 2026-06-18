from fpdf import FPDF
import sys
sys.stderr = open("D:\\Jacky\\AI-Native DevOps\\ai-incident-commander\\outreach\\_debug.log", "w")
sys.stdout = sys.stderr

print("starting", flush=True)
pdf = FPDF()
print("FPDF ok", flush=True)
pdf.add_page()
print("add_page ok", flush=True)

fpath = "C:\\Windows\\Fonts\\simhei.ttf"
print(f"check font exists: {__import__('os').path.exists(fpath)}", flush=True)

pdf.add_font("SimHei", "", fpath, uni=True)
print("font added", flush=True)

pdf.set_font("SimHei", "", 16)
pdf.cell(0, 10, "AI Incident Commander", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("SimHei", "", 10)
pdf.cell(0, 6, "Founding Partner Program", new_x="LMARGIN", new_y="NEXT")

out = "D:\\Jacky\\AI-Native DevOps\\ai-incident-commander\\outreach\\AI_Incident_Commander_FP_Program.pdf"
pdf.output(out)
print(f"output done: {__import__('os').path.exists(out)}", flush=True)
