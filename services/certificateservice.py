import os
import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_training_certificate(
    employee_name: str,
    employee_email: str,
    course_title: str,
    course_code: str,
    completion_date: str,
    score: str,
    passed: bool,
    certificate_id: str
) -> BytesIO:
    """
    Generate a PDF certificate for completed training
    """
    # Create a BytesIO buffer to store the PDF
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.darkgreen
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    center_style = ParagraphStyle(
        'CenterStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    # Add company header
    story.append(Paragraph("QUALITY MANAGEMENT SYSTEM", title_style))
    story.append(Spacer(1, 20))
    
    # Add certificate title
    story.append(Paragraph("CERTIFICATE OF COMPLETION", subtitle_style))
    story.append(Spacer(1, 30))
    
    # Add certificate ID
    story.append(Paragraph(f"Certificate ID: {certificate_id}", center_style))
    story.append(Spacer(1, 20))
    
    # Add main content
    story.append(Paragraph(
        f"This is to certify that <b>{employee_name}</b> has successfully completed the training course:",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Course details in a table
    course_data = [
        ["Course Title:", course_title],
        ["Course Code:", course_code],
        ["Completion Date:", completion_date],
        ["Score:", score],
        ["Status:", "PASSED" if passed else "FAILED"]
    ]
    
    course_table = Table(course_data, colWidths=[2*inch, 4*inch])
    course_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(course_table)
    story.append(Spacer(1, 30))
    
    # Add completion message
    if passed:
        story.append(Paragraph(
            "This certificate confirms that the participant has met all requirements and demonstrated "
            "proficiency in the course material.",
            normal_style
        ))
    else:
        story.append(Paragraph(
            "Note: This participant did not achieve the required passing score. "
            "Additional training may be required.",
            normal_style
        ))
    
    story.append(Spacer(1, 40))
    
    # Add signature section
    signature_data = [
        ["", "", ""],
        ["_________________", "_________________", "_________________"],
        ["Employee Signature", "Trainer Signature", "Date"],
    ]
    
    signature_table = Table(signature_data, colWidths=[2*inch, 2*inch, 2*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    story.append(signature_table)
    story.append(Spacer(1, 30))
    
    # Add footer
    story.append(Paragraph(
        f"Certificate generated on: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        center_style
    ))
    
    # Build the PDF
    doc.build(story)
    
    # Reset buffer position
    buffer.seek(0)
    return buffer

def save_certificate_to_file(certificate_buffer: BytesIO, filename: str) -> str:
    """
    Save the certificate buffer to a file and return the file path
    """
    # Create certificates directory if it doesn't exist
    certificates_dir = "uploads/certificates"
    os.makedirs(certificates_dir, exist_ok=True)
    
    # Save the PDF
    file_path = os.path.join(certificates_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(certificate_buffer.getvalue())
    
    return file_path 