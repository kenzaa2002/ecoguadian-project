import io
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.prediction import Prediction
from app.models.dashboard import Dashboard

router = APIRouter()

def _build_pdf(user, dashboard, predictions):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    GREEN = colors.HexColor("#16a34a"); LGRAY = colors.HexColor("#f0fdf4")
    title_style = ParagraphStyle("Title", parent=styles["Title"], textColor=GREEN, fontSize=22, spaceAfter=4)
    sub_style   = ParagraphStyle("Sub",   parent=styles["Normal"], textColor=colors.grey, fontSize=10, spaceAfter=12)
    h2_style    = ParagraphStyle("H2",    parent=styles["Heading2"], textColor=GREEN, fontSize=13, spaceBefore=12, spaceAfter=4)
    story = []
    story.append(Paragraph("🌿 EcoGuardian Energy Report", title_style))
    story.append(Paragraph(f"House: <b>{dashboard.name}</b> | Owner: {user.full_name or user.username} | Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC", sub_style))
    story.append(HRFlowable(width="100%", color=GREEN, thickness=1))
    story.append(Spacer(1, 0.3*cm))
    if predictions:
        avg_kwh = sum(p.avg_monthly_kwh or 0 for p in predictions) / len(predictions)
        total_cost = sum((p.month1_cost or 0)+(p.month2_cost or 0)+(p.month3_cost or 0) for p in predictions)
        peak_kwh = max((p.peak_kwh or 0) for p in predictions)
        story.append(Paragraph("Summary Statistics", h2_style))
        tbl_data = [["Metric","Value"],["Total Predictions",str(len(predictions))],
            ["Average Monthly kWh",f"{avg_kwh:.1f} kWh"],["Peak Monthly kWh",f"{peak_kwh:.1f} kWh"],
            ["Total Estimated Cost",f"{total_cost:.2f} TND"],["Energy Rate",f"{settings.ENERGY_PRICE_TND} TND/kWh"]]
        t = Table(tbl_data, colWidths=[9*cm, 7*cm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LGRAY]),
            ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story.append(t); story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Prediction History", h2_style))
    table_data = [["Date","Appliance","Avg kWh/mo","Peak kWh","M1 Cost (TND)"]]
    for p in predictions[:20]:
        table_data.append([p.created_at.strftime("%d %b %Y") if p.created_at else "–",
            p.appliance_label or "–", f"{p.avg_monthly_kwh:.1f}" if p.avg_monthly_kwh else "–",
            f"{p.peak_kwh:.1f}" if p.peak_kwh else "–", f"{p.month1_cost:.2f}" if p.month1_cost else "–"])
    th = Table(table_data, colWidths=[3.2*cm,4*cm,3.2*cm,3.2*cm,3.4*cm])
    th.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LGRAY]),
        ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),9),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(th)
    doc.build(story)
    return buffer.getvalue()

@router.get("/{dashboard_id}/pdf")
def export_pdf_report(dashboard_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current_user.id).first()
    if not dashboard: raise HTTPException(status_code=404, detail="Dashboard not found")
    predictions = db.query(Prediction).filter(
        Prediction.user_id == current_user.id, Prediction.dashboard_id == dashboard_id
    ).order_by(Prediction.created_at.desc()).limit(50).all()
    try:
        pdf_bytes = _build_pdf(current_user, dashboard, predictions)
    except ImportError:
        raise HTTPException(status_code=500, detail="ReportLab not installed. Run: pip install reportlab")
    filename = f"ecoguardian_{dashboard.name.replace(' ','_')}.pdf"
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
