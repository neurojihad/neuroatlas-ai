from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER


def create_cv_pdf():
    doc = SimpleDocTemplate("../private/Dmitry_Astakhov_CV.pdf", pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=6,
                                 textColor=colors.HexColor('#1a237e'), fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=16, spaceAfter=12,
                                    textColor=colors.HexColor('#0d47a1'), fontName='Helvetica')
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=6,
                                   textColor=colors.HexColor('#0d47a1'), fontName='Helvetica-Bold', spaceBefore=12)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=4,
                                  fontName='Helvetica', leading=14)
    bullet_style = ParagraphStyle('BulletStyle', parent=normal_style, leftIndent=20, fontSize=10, leading=14)
    contact_style = ParagraphStyle('ContactStyle', parent=normal_style, fontSize=9,
                                   textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)

    story = []
    story.append(Paragraph('DMITRY ASTAKHOV', title_style))
    story.append(Paragraph('Python Backend & AI Engineer', subtitle_style))
    contact_text = "Phone: +7 (911) 137-6892 | Email: dmastx108@yandex.ru | Telegram: @dm_astx<br/>Location: Saint Petersburg, Russia | English: C1 (Fluent)"
    story.append(Paragraph(contact_text, contact_style))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph('PROFESSIONAL SUMMARY', heading_style))
    summary_text = "Backend Developer with 8+ years of experience building production systems in Python, FastAPI, and microservices architecture. Currently transitioning into AI Engineering with hands-on experience in LLM-based applications, RAG systems, and healthcare AI platforms. Strong background in payment systems, distributed architectures, and API design. Passionate about building AI-powered solutions for healthcare and biotech domains."
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph('CORE SKILLS', heading_style))
    skills_data = [
        ['Programming:', 'Python (Advanced), JavaScript, PHP, C#'],
        ['Backend:', 'FastAPI, REST API, SQLAlchemy, Redis, Kafka, Docker'],
        ['Databases:', 'PostgreSQL, MySQL, ClickHouse, MS SQL Server'],
        ['DevOps:', 'Linux, Docker, Git, Prometheus, Grafana'],
        ['AI/ML:', 'LLM, RAG, Embeddings, PyTorch (learning)']
    ]
    skills_table = Table(skills_data, colWidths=[2.2 * inch, 4 * inch])
    skills_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(skills_table)
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph('WORK EXPERIENCE', heading_style))
    story.append(Paragraph('<b>Python Developer</b> | Atom', normal_style))
    story.append(Paragraph('<i>April 2024 - Present</i>', normal_style))
    story.append(
        Paragraph('• Designed and implemented payment gateway backend services using FastAPI, PostgreSQL, and Kafka',
                  bullet_style))
    story.append(Paragraph('• Architected REST APIs for payment processing, subscriptions, invoices, and integrations',
                           bullet_style))
    story.append(Paragraph('• Integrated with payment providers and cloud services; managed event-driven architecture',
                           bullet_style))
    story.append(Paragraph('• Conducted code reviews, wrote comprehensive tests, and participated in incident analysis',
                           bullet_style))
    story.append(Paragraph('• Contributed to architectural evolution and technical decision-making', bullet_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph('<b>Python Developer</b> | Innotech Group', normal_style))
    story.append(Paragraph('<i>October 2018 - March 2024 | 5.5 years</i>', normal_style))
    story.append(
        Paragraph('• Built optimization and strategic modeling platforms using FastAPI and Python', bullet_style))
    story.append(
        Paragraph('• Integrated with external services and developed REST API analysis utilities', bullet_style))
    story.append(
        Paragraph('• Implemented parallel computing solutions using scipy-stack and Linux environment', bullet_style))
    story.append(Paragraph('• Wrote unit and integration tests, conducted code reviews', bullet_style))
    story.append(Paragraph('• Maintained and improved legacy codebase while developing new features', bullet_style))
    story.append(Paragraph('• Integrated projects with internal and external enterprise services', bullet_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph('AI & ML PROJECTS', heading_style))
    story.append(Paragraph('<b>NeuroAtlas AI</b> — Healthcare Research Platform', normal_style))
    story.append(Paragraph('<i>Personal AI Project</i>', normal_style))
    story.append(
        Paragraph('• Built AI-powered research assistant using RAG (Retrieval-Augmented Generation) architecture',
                  bullet_style))
    story.append(
        Paragraph('• Designed document ingestion pipelines for biomedical publications (PubMed, clinical research)',
                  bullet_style))
    story.append(
        Paragraph('• Implemented semantic search using embeddings with vector database integration', bullet_style))
    story.append(Paragraph('• Integrated LLM-based research assistant workflows', bullet_style))
    story.append(Paragraph('• Built backend API layer using FastAPI for scientific knowledge extraction', bullet_style))
    story.append(Paragraph('<b>Tech:</b> Python, FastAPI, PostgreSQL, Vector DB, LLM, RAG, Embeddings', normal_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph('EDUCATION', heading_style))
    story.append(Paragraph('<b>Bachelor of Information Systems and Technology</b>', normal_style))
    story.append(
        Paragraph('Saint Petersburg National Research University of IT, Mechanics and Optics (ITMO)', normal_style))
    story.append(Paragraph('<i>Graduated: 2012</i>', normal_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph('LANGUAGES', heading_style))
    story.append(Paragraph('• Russian — Native', normal_style))
    story.append(Paragraph('• English — C1 (Fluent), professional working proficiency', normal_style))
    story.append(Paragraph('• Spanish — A2 (Basic)', normal_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph('ADDITIONAL INFORMATION', heading_style))
    story.append(Paragraph('• Driver\'s license: Category B', normal_style))
    story.append(Paragraph('• Location: Saint Petersburg, Russia', normal_style))
    story.append(Paragraph('• Remote work: Fully available', normal_style))

    doc.build(story)
    print('✅ PDF created: Dmitry_Astakhov_CV.pdf')


if __name__ == "__main__":
    create_cv_pdf()
