import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas to compute total page count and add running footer.
    """
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
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Draw running header
        self.drawString(54, 750, "NEPHROINSIGHT AI — CLINICAL DECISION SUPPORT REPORT")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 742, letter[0] - 54, 742)
        
        # Draw running footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 40, page_text)
        self.drawString(54, 40, "CONFIDENTIAL — FOR MEDICAL PROFESSIONAL USE ONLY")
        self.line(54, 52, letter[0] - 54, 52)
        
        self.restoreState()

class ReportPDFService:
    @staticmethod
    def generate_report(prediction, patient, record, recommendations, hospital_name, doctor_name, output_dir=None):
        """
        Generates a professional clinical PDF report.
        Returns:
            str: Path to the generated PDF.
        """
        if output_dir is None:
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, 'reports')
            
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Report_{prediction.report_id}.pdf"
        pdf_path = os.path.join(output_dir, filename)
        
        # Set up document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=72, bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        
        # Modify existing styles to avoid adding duplicate styles
        styles['Normal'].textColor = colors.HexColor("#0F172A")
        styles['Normal'].fontSize = 9
        styles['Normal'].leading = 13
        
        # Create custom ParagraphStyles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#2563EB")
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0EA5E9")
        )
        
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=6,
            keepWithNext=True
        )
        
        meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748B")
        )
        
        risk_positive_style = ParagraphStyle(
            'RiskPositive',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#DC2626") # Danger red
        )
        
        risk_negative_style = ParagraphStyle(
            'RiskNegative',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#16A34A") # Success green
        )
        
        bullet_style = ParagraphStyle(
            'ReportBullet',
            parent=styles['Normal'],
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3
        )
        
        story = []
        
        # 1. Header (Logo Block & Hospital Details)
        # We build a table for the header
        logo_data = [
            [
                Paragraph("<b>NephroInsight AI</b><br/><font color='#0EA5E9'>Explainable Kidney Health CDSS</font>", title_style),
                Paragraph(f"<b>{hospital_name}</b><br/>{doctor_name}<br/>Department of Nephrology", ParagraphStyle('HospDetails', parent=styles['Normal'], alignment=2, leading=13))
            ]
        ]
        header_table = Table(logo_data, colWidths=[3.0 * inch, 4.0 * inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
        
        # 2. Report Metadata Block
        meta_data = [
            [
                Paragraph("REPORT ID:", meta_label_style), Paragraph(f"<b>{prediction.report_id}</b>", styles['Normal']),
                Paragraph("DATE GENERATED:", meta_label_style), Paragraph(f"<b>{prediction.created_at.strftime('%Y-%m-%d %H:%M:%S')}</b>", styles['Normal'])
            ],
            [
                Paragraph("REFERRING CLINICIAN:", meta_label_style), Paragraph(f"<b>{doctor_name}</b>", styles['Normal']),
                Paragraph("METHODOLOGY:", meta_label_style), Paragraph("<b>Hybrid Ensemble Learning</b>", styles['Normal'])
            ]
        ]
        meta_table = Table(meta_data, colWidths=[1.8 * inch, 1.7 * inch, 1.5 * inch, 2.0 * inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))
        
        # 3. Patient Information
        story.append(Paragraph("PATIENT DEMOGRAPHICS", section_heading))
        patient_data = [
            [
                Paragraph("PATIENT NAME:", meta_label_style), Paragraph(patient.name, styles['Normal']),
                Paragraph("PATIENT ID:", meta_label_style), Paragraph(patient.patient_id, styles['Normal'])
            ],
            [
                Paragraph("DATE OF BIRTH:", meta_label_style), Paragraph(patient.dob.strftime('%Y-%m-%d'), styles['Normal']),
                Paragraph("GENDER:", meta_label_style), Paragraph(patient.gender, styles['Normal'])
            ],
            [
                Paragraph("CONTACT NO:", meta_label_style), Paragraph(patient.contact, styles['Normal']),
                Paragraph("EMAIL:", meta_label_style), Paragraph(patient.email or 'N/A', styles['Normal'])
            ]
        ]
        patient_table = Table(patient_data, colWidths=[1.5 * inch, 2.0 * inch, 1.2 * inch, 2.3 * inch])
        patient_table.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 15))
        
        # 4. Diagnostic & Prediction Outcome
        story.append(Paragraph("RISK EVALUATION REPORT", section_heading))
        
        outcome_style = risk_positive_style if prediction.prediction_outcome == 'CKD Positive' else risk_negative_style
        
        # Mini Risk Gauge representation in PDF
        risk_percent = recommendations['risk_percent']
        gauge_bar_color = colors.HexColor("#DC2626") if prediction.prediction_outcome == 'CKD Positive' else colors.HexColor("#16A34A")
        
        # Create a simple representation of a risk bar in a Table
        gauge_width = 4.0 * inch * (risk_percent / 100.0)
        remaining_width = 4.0 * inch - gauge_width
        
        gauge_bar_data = [["", ""]]
        gauge_bar_table = Table(gauge_bar_data, colWidths=[gauge_width, remaining_width])
        gauge_bar_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), gauge_bar_color),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        prediction_data = [
            [
                Paragraph("PREDICTION OUTCOME:", meta_label_style),
                Paragraph(f"{prediction.prediction_outcome.upper()}", outcome_style),
                Paragraph("CKD RISK PROBABILITY:", meta_label_style),
                Paragraph(f"<b>{risk_percent}%</b>", outcome_style)
            ],
            [
                Paragraph("DECISION THRESHOLD:", meta_label_style),
                Paragraph(f"{prediction.threshold_used * 100}%", styles['Normal']),
                Paragraph("RISK METER INDICATOR:", meta_label_style),
                gauge_bar_table
            ]
        ]
        
        prediction_table = Table(prediction_data, colWidths=[1.8 * inch, 1.7 * inch, 1.5 * inch, 2.0 * inch])
        prediction_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
        ]))
        story.append(prediction_table)
        story.append(Spacer(1, 20))
        
        # Page Break to keep visual AI charts together on Page 2
        story.append(PageBreak())
        
        # Page 2: Explainable AI Summary
        story.append(Paragraph("EXPLAINABLE AI (XAI) ANALYTICS", section_heading))
        story.append(Paragraph("The visual models below present local post-hoc explanations for this specific patient decision, describing how clinical features shifted the ensemble prediction.", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Load SHAP and LIME images if they exist
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        shap_img_path = os.path.join(base_dir, 'static', prediction.shap_waterfall_path) if prediction.shap_waterfall_path else None
        lime_img_path = os.path.join(base_dir, 'static', prediction.lime_plot_path) if prediction.lime_plot_path else None
        
        chart_elements = []
        if shap_img_path and os.path.exists(shap_img_path):
            chart_elements.append([
                Paragraph("<b>SHAP Attribution Explanation (Local Waterfall)</b>", styles['Normal']),
                Image(shap_img_path, width=3.2 * inch, height=2.1 * inch)
            ])
        else:
            chart_elements.append([
                Paragraph("<b>SHAP Attribution Explanation</b>", styles['Normal']),
                Paragraph("<font color='#EF4444'>[SHAP Waterfall Visualization Unavailable]</font>", styles['Normal'])
            ])
            
        if lime_img_path and os.path.exists(lime_img_path):
            chart_elements.append([
                Paragraph("<b>LIME Contribution Explanation (Local Coefficients)</b>", styles['Normal']),
                Image(lime_img_path, width=3.2 * inch, height=2.1 * inch)
            ])
        else:
            chart_elements.append([
                Paragraph("<b>LIME Contribution Explanation</b>", styles['Normal']),
                Paragraph("<font color='#EF4444'>[LIME Pyplot Visualization Unavailable]</font>", styles['Normal'])
            ])
            
        # Put charts side-by-side or stacked
        # Let's stack them nicely
        chart_table_data = [
            [chart_elements[0][0], chart_elements[1][0]],
            [chart_elements[0][1], chart_elements[1][1]]
        ]
        chart_table = Table(chart_table_data, colWidths=[3.5 * inch, 3.5 * inch])
        chart_table.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 4),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(chart_table)
        story.append(Spacer(1, 10))
        
        # 5. Doctor & Patient Explanations
        explanation_data = [
            [
                Paragraph("<b>CLINICIAN INTERPRETATION (LIME/SHAP SUMMARY)</b>", meta_label_style),
                Paragraph("<b>PATIENT-FRIENDLY TRANSLATION</b>", meta_label_style)
            ],
            [
                Paragraph(prediction.doctor_notes or "No notes added.", styles['Normal']),
                Paragraph(recommendations.get('patient_explanation', "No patient translation compiled."), styles['Normal'])
            ]
        ]
        explanation_table = Table(explanation_data, colWidths=[3.5 * inch, 3.5 * inch])
        explanation_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(explanation_table)
        story.append(Spacer(1, 15))
        
        story.append(PageBreak())
        
        # Page 3: Clinical Recommendations & Action Plan
        story.append(Paragraph("CLINICAL RECOMMENDATIONS & ACTION PLAN", section_heading))
        story.append(Paragraph("Customized protocols generated dynamically based on the patient's individual serum markers and risk classification.", styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Build recommendations bullet lists
        recs_content = []
        
        # Grouped by type
        if recommendations.get('emergency_alerts'):
            recs_content.append(Paragraph("<b><font color='#DC2626'>EMERGENCY ALERTS / WARNINGS:</font></b>", styles['Normal']))
            for item in recommendations['emergency_alerts']:
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            recs_content.append(Spacer(1, 5))
            
        if recommendations.get('clinical_followups'):
            recs_content.append(Paragraph("<b>CLINICAL FOLLOW-UP:</b>", styles['Normal']))
            for item in recommendations['clinical_followups']:
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            recs_content.append(Spacer(1, 5))
            
        if recommendations.get('laboratory_tests'):
            recs_content.append(Paragraph("<b>RECOMMENDED LABORATORY TESTS:</b>", styles['Normal']))
            for item in recommendations['laboratory_tests']:
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            recs_content.append(Spacer(1, 5))
            
        if recommendations.get('diet_suggestions'):
            recs_content.append(Paragraph("<b>DIETARY ADJUSTMENTS:</b>", styles['Normal']))
            for item in recommendations['diet_suggestions']:
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            recs_content.append(Spacer(1, 5))
            
        if recommendations.get('lifestyle_advice') or recommendations.get('hydration_advice') or recommendations.get('exercise_suggestions'):
            recs_content.append(Paragraph("<b>LIFESTYLE & SUPPORTIVE ADVICE:</b>", styles['Normal']))
            for item in recommendations.get('lifestyle_advice', []):
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            for item in recommendations.get('hydration_advice', []):
                recs_content.append(Paragraph(f"• {item}", bullet_style))
            for item in recommendations.get('exercise_suggestions', []):
                recs_content.append(Paragraph(f"• {item}", bullet_style))
                
        # Put recommendations in a box
        recs_box = KeepTogether([
            Table([[recs_content]], colWidths=[7.0 * inch], style=[
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFFFFF")),
                ('PADDING', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ])
        ])
        story.append(recs_box)
        story.append(Spacer(1, 20))
        
        # 6. Signature Block
        sig_data = [
            [
                Paragraph("<b>PHYSICIAN NOTES:</b><br/>This report represents diagnostic support generated using ensemble learning and SHAP/LIME interpretations. Final clinical judgments rest solely on the attending physician.", ParagraphStyle('PhysDisclaimer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#64748B"))),
                Paragraph("<b>PHYSICIAN SIGNATURE:</b><br/><br/>___________________________________<br/>Dr. Signature Block", ParagraphStyle('PhysSig', parent=styles['Normal'], alignment=2))
            ]
        ]
        sig_table = Table(sig_data, colWidths=[4.0 * inch, 3.0 * inch])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(Spacer(1, 15))
        story.append(KeepTogether(sig_table))
        
        # Build Document
        doc.build(story, canvasmaker=NumberedCanvas)
        return pdf_path
