from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os

# Попытка зарегистрировать шрифт с поддержкой кириллицы
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Пробуем разные системные шрифты
    fonts_to_try = [
        'DejaVuSans.ttf',
        'FreeSerif.ttf',
        'Arial.ttf',
        'TimesNewRoman.ttf',
        'LiberationSerif.ttf'
    ]
    font_registered = False
    for font in fonts_to_try:
        try:
            pdfmetrics.registerFont(TTFont('RussianFont', font))
            font_registered = True
            break
        except:
            continue
    if not font_registered:
        print("⚠️ Шрифт с кириллицей не найден, текст может отображаться некорректно")
        print("Установи: sudo apt-get install fonts-dejavu (Linux) или скачай DejaVuSans.ttf")
except:
    print("⚠️ Не удалось зарегистрировать шрифт, кириллица может не отображаться")


def create_cv_pdf_russian():
    """Создать PDF резюме на русском языке"""

    doc = SimpleDocTemplate("Астахов_Дмитрий_Резюме.pdf", pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()

    # Стили с поддержкой кириллицы
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=6,
        textColor=colors.HexColor('#1a237e'),
        fontName='Helvetica-Bold' if not font_registered else 'RussianFont',
        alignment=0  # LEFT
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#0d47a1'),
        fontName='Helvetica' if not font_registered else 'RussianFont',
        alignment=0
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        textColor=colors.HexColor('#0d47a1'),
        fontName='Helvetica-Bold' if not font_registered else 'RussianFont',
        spaceBefore=12,
        alignment=0
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        fontName='Helvetica' if not font_registered else 'RussianFont',
        leading=14,
        alignment=0
    )

    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=normal_style,
        leftIndent=20,
        fontSize=10,
        leading=14,
        alignment=0
    )

    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=normal_style,
        fontSize=9,
        textColor=colors.HexColor('#546e7a'),
        alignment=TA_LEFT
    )

    story = []

    # ============================================
    # ЗАГОЛОВОК
    # ============================================
    story.append(Paragraph('АСТАХОВ ДМИТРИЙ', title_style))
    story.append(Paragraph('Python Backend & AI Инженер', subtitle_style))

    # Контакты
    contact_text = """Телефон: +7 (9921) 594-83-93 | Email: dmastx108@yandex.ru | Telegram: @neurojihad<br/>
    Санкт-Петербург, Россия | Английский: C1 (Свободно) | Испанский: B1 (Продвинутый)"""
    story.append(Paragraph(contact_text, contact_style))
    story.append(Spacer(1, 0.3 * inch))

    # ============================================
    # ПРОФЕССИОНАЛЬНЫЙ ОБЗОР
    # ============================================
    story.append(Paragraph('ПРОФЕССИОНАЛЬНЫЙ ОБЗОР', heading_style))
    summary_text = """Backend-разработчик с 8+ годами опыта создания продуктовых систем на Python, FastAPI и микросервисной архитектуре.
    В настоящее время развиваюсь в сторону AI-инженерии с практическим опытом в LLM-приложениях, RAG-системах и AI-платформах для здравоохранения.
    Сильный бэкграунд в платежных системах, распределенных архитектурах и проектировании API.
    Увлечен созданием AI-решений для медицины и биотехнологий."""
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 0.1 * inch))

    # ============================================
    # КЛЮЧЕВЫЕ НАВЫКИ
    # ============================================
    story.append(Paragraph('КЛЮЧЕВЫЕ НАВЫКИ', heading_style))
    skills_data = [
        ['Программирование:', 'Python (Продвинутый), JavaScript, PHP, C#'],
        ['Backend:', 'FastAPI, REST API, SQLAlchemy, Redis, Kafka, Docker'],
        ['Базы данных:', 'PostgreSQL, MySQL, ClickHouse, MS SQL Server, Redis'],
        ['DevOps:', 'Linux, Docker, Git, Prometheus, Grafana'],
        ['AI/ML:', 'LLM, RAG, Embeddings, XGBoost']
    ]

    skills_table = Table(skills_data, colWidths=[2.2 * inch, 4 * inch])
    skills_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica' if not font_registered else 'RussianFont'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold' if not font_registered else 'RussianFont'),
    ]))
    story.append(skills_table)
    story.append(Spacer(1, 0.1 * inch))

    # ============================================
    # ОПЫТ РАБОТЫ
    # ============================================
    story.append(Paragraph('ОПЫТ РАБОТЫ', heading_style))

    # Опыт 1 - Атом
    story.append(Paragraph('<b>Python Разработчик</b> | Атом', normal_style))
    story.append(Paragraph('<i>Апрель 2024 - Настоящее время</i>', normal_style))
    story.append(Paragraph(
        '• Разработал и внедрил backend-сервисы платежного шлюза с использованием FastAPI, PostgreSQL и Kafka',
        bullet_style))
    story.append(
        Paragraph('• Спроектировал REST API для обработки платежей, подписок, инвойсов и интеграций', bullet_style))
    story.append(
        Paragraph('• Интегрировал платежных провайдеров и облачные сервисы; управлял event-driven архитектурой',
                  bullet_style))
    story.append(
        Paragraph('• Проводил код-ревью, писал комплексные тесты и участвовал в анализе инцидентов', bullet_style))
    story.append(Paragraph('• Участвовал в эволюции архитектуры и принятии технических решений', bullet_style))
    story.append(Spacer(1, 0.1 * inch))

    # Опыт 2 - Иннотех
    story.append(Paragraph('<b>Python Разработчик</b> | Иннотех, Группа компаний', normal_style))
    story.append(Paragraph('<i>Октябрь 2018 - Март 2024 | 5.5 лет</i>', normal_style))
    story.append(Paragraph('• Разработал платформы для оптимизации и стратегического моделирования на FastAPI и Python',
                           bullet_style))
    story.append(Paragraph('• Интегрировал внешние сервисы и разработал утилиты для анализа REST API', bullet_style))
    story.append(Paragraph('• Реализовал параллельные вычисления на scipy-stack в среде Linux', bullet_style))
    story.append(Paragraph('• Писал модульные и интеграционные тесты, проводил код-ревью', bullet_style))
    story.append(Paragraph('• Поддерживал и улучшал существующий код, разрабатывал новые функции', bullet_style))
    story.append(Paragraph('• Интегрировал проекты с внутренними и внешними корпоративными сервисами', bullet_style))
    story.append(Spacer(1, 0.2 * inch))

    # ============================================
    # AI ПРОЕКТЫ
    # ============================================
    story.append(Paragraph('AI И ML ПРОЕКТЫ', heading_style))

    # ============================================
    # ОБРАЗОВАНИЕ
    # ============================================
    story.append(Paragraph('ОБРАЗОВАНИЕ', heading_style))
    story.append(Paragraph('<b>Бакалавр информационных систем и технологий</b>', normal_style))
    story.append(Paragraph(
        'Санкт-Петербургский национальный исследовательский университет информационных технологий, механики и оптики (ИТМО)',
        normal_style))
    story.append(Paragraph('<i>Окончил: 2012</i>', normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # ============================================
    # ЯЗЫКИ
    # ============================================
    story.append(Paragraph('ЯЗЫКИ', heading_style))
    story.append(Paragraph('• Русский — Родной', normal_style))
    story.append(Paragraph('• Английский — C1, профессиональный рабочий уровень', normal_style))
    story.append(Paragraph('• Испанский — B1', normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # ============================================
    # ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
    # ============================================
    story.append(Paragraph('ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ', heading_style))
    story.append(Paragraph('• Водительское удостоверение: Категория A, B', normal_style))
    story.append(Paragraph('• Местоположение: Санкт-Петербург, Россия', normal_style))

    # Создание PDF
    doc.build(story)
    print('✅ PDF создан: Астахов_Дмитрий_Резюме.pdf')
    return "Астахов_Дмитрий_Резюме.pdf"


if __name__ == "__main__":
    create_cv_pdf_russian()
