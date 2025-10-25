"""Dataset exporters for CSV, Excel, and PDF formats."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def export_excel(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")


def export_pdf(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _build_pdf(df)
    pdf.output(str(path))


def _build_pdf(df: pd.DataFrame) -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Startup Internship Report", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow():%Y-%m-%d %H:%M UTC}", ln=True)
    pdf.cell(0, 8, f"Total listings: {len(df)}", ln=True)
    pdf.ln(4)

    for _, row in df.iterrows():
        _write_listing(pdf, row)
        pdf.ln(4)

    return pdf


def _write_listing(pdf: FPDF, row: pd.Series) -> None:
    pdf.set_font("Helvetica", "B", 12)
    # Clean text to avoid Unicode issues and truncate if too long
    company = str(row.get('company', 'Unknown'))[:50].encode('ascii', 'ignore').decode('ascii')
    role = str(row.get('role_title', ''))[:50].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 6, f"{company} - {role}")
    pdf.set_font("Helvetica", size=11)
    location = str(row.get("location") or "N/A")[:20].encode('ascii', 'ignore').decode('ascii')
    pay = str(row.get("pay") or "N/A")[:20].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 5, f"Location: {location}")
    pdf.multi_cell(0, 5, f"Pay: {pay}")
    stack = str(row.get("recommended_tech_stack") or "")[:100].encode('ascii', 'ignore').decode('ascii')
    if stack:
        pdf.multi_cell(0, 5, f"Stack: {stack}")
    pdf.set_font("Helvetica", size=10)
    responsibilities = str(row.get("responsibilities") or "")[:200].encode('ascii', 'ignore').decode('ascii')
    if responsibilities:
        pdf.multi_cell(0, 4, responsibilities + ("..." if len(str(row.get("responsibilities") or "")) > 200 else ""))
    url = str(row.get("source_url") or "")[:100].encode('ascii', 'ignore').decode('ascii')
    if url:
        pdf.set_text_color(0, 0, 200)
        pdf.multi_cell(0, 4, url)
        pdf.set_text_color(0, 0, 0)

