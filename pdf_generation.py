from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os
import tempfile


class PDFGenerator:
    """Генератор PDF с поддержкой русского языка"""

    @staticmethod
    def register_russian_font():
        """Регистрация шрифта с поддержкой кириллицы"""
        try:
            # Ищем шрифт Arial в стандартных местах
            font_paths = [
                'C:\\Windows\\Fonts\\arial.ttf',  # Windows
                'C:\\Windows\\Fonts\\arialbd.ttf',  # Windows Bold
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux
                '/System/Library/Fonts/Arial.ttf',  # macOS
                'arial.ttf'  # Текущая директория
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        # Регистрируем обычный и жирный шрифт
                        pdfmetrics.registerFont(TTFont('Arial', font_path))

                        # Пробуем зарегистрировать жирный вариант
                        if 'bd' in font_path.lower() or 'bold' in font_path.lower():
                            pdfmetrics.registerFont(TTFont('Arial-Bold', font_path))
                        else:
                            # Если не нашли жирный, используем тот же
                            pdfmetrics.registerFont(TTFont('Arial-Bold', font_path))

                        return True
                    except Exception as e:
                        print(f"Не удалось зарегистрировать шрифт {font_path}: {e}")
                        continue

            # Если не нашли Arial, пробуем использовать DejaVu (часто есть в Linux)
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', 'DejaVuSans-Bold.ttf'))
                return True
            except:
                pass

            return False
        except Exception as e:
            print(f"Ошибка регистрации шрифта: {e}")
            return False

    @staticmethod
    def generate_transaction_history(transactions, user_info, period_info=""):
        """Генерация PDF с историей транзакций"""

        # Создаем временный файл
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"История_транзакций_{user_info.get('id', 'user')}_{timestamp}.pdf"
        output_file = os.path.join(temp_dir, filename)

        # Регистрируем русский шрифт
        font_registered = PDFGenerator.register_russian_font()

        # Определяем используемые шрифты
        if font_registered:
            # Проверяем какие шрифты доступны
            try:
                pdfmetrics.getFont('Arial-Bold')
                normal_font = 'Arial'
                bold_font = 'Arial-Bold'
            except:
                try:
                    pdfmetrics.getFont('DejaVu-Bold')
                    normal_font = 'DejaVu'
                    bold_font = 'DejaVu-Bold'
                except:
                    # Возвращаемся к стандартным шрифтам
                    normal_font = 'Helvetica'
                    bold_font = 'Helvetica-Bold'
        else:
            normal_font = 'Helvetica'
            bold_font = 'Helvetica-Bold'

        # Создаем документ
        doc = SimpleDocTemplate(
            output_file,
            pagesize=landscape(A4),
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            encoding='utf-8'
        )

        elements = []
        styles = getSampleStyleSheet()

        # Создаем стили с русскими шрифтами
        title_style = ParagraphStyle(
            'RussianTitle',
            parent=styles['Heading1'],
            fontName=bold_font,
            fontSize=16,
            spaceAfter=20,
            alignment=1
        )

        subtitle_style = ParagraphStyle(
            'RussianSubtitle',
            parent=styles['Heading2'],
            fontName=bold_font,
            fontSize=12,
            spaceAfter=10
        )

        normal_style = ParagraphStyle(
            'RussianNormal',
            parent=styles['Normal'],
            fontName=normal_font,
            fontSize=10
        )

        # Заголовок (русский текст напрямую)
        title_text = "История транзакций - Crypto Wallet"
        elements.append(Paragraph(title_text, title_style))

        # Информация о пользователе
        user_text = f"Пользователь: {user_info.get('name', '')}"
        elements.append(Paragraph(user_text, subtitle_style))

        phone_text = f"Телефон: {user_info.get('phone', '')}"
        elements.append(Paragraph(phone_text, normal_style))

        # Период и дата
        period_text = f"Период: {period_info}"
        date_text = f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        elements.append(Paragraph(period_text, normal_style))
        elements.append(Paragraph(date_text, normal_style))

        elements.append(Spacer(1, 20))

        # Подготавливаем данные для таблицы
        data = []

        # Заголовки таблицы
        headers = ["Дата", "Тип", "Валюта", "Сумма", "Контрагент", "Статус"]
        data.append(headers)

        # Данные транзакций
        for t in transactions:
            row = [
                t.get('date', ''),
                t.get('type', ''),
                t.get('currency', ''),
                f"{t.get('amount', 0):.8f}",
                t.get('counterparty', '')[:20],  # Ограничиваем длину
                t.get('status', '')
            ]
            data.append(row)

        # Создаем таблицу
        col_widths = [1.5 * inch, 1 * inch, 0.8 * inch, 1 * inch, 1.5 * inch, 1 * inch]
        table = Table(data, colWidths=col_widths)

        # Стили таблицы
        style = TableStyle([
            # Заголовки
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E8B57')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Данные
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), normal_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Выравнивание
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),
        ])

        # Цвета для статусов
        for i, t in enumerate(transactions, start=1):
            status = t.get('status', '')
            if '✅' in status or 'Выполнено' in status:
                style.add('TEXTCOLOR', (5, i), (5, i), colors.green)
            elif '⏳' in status or 'Ожидание' in status:
                style.add('TEXTCOLOR', (5, i), (5, i), colors.orange)
            elif '❌' in status or 'Отменено' in status or 'Ошибка' in status:
                style.add('TEXTCOLOR', (5, i), (5, i), colors.red)

        table.setStyle(style)
        elements.append(table)

        # Итоги
        elements.append(Spacer(1, 20))

        total_count = len(transactions)
        completed = len([t for t in transactions if '✅' in t.get('status', '') or 'Выполнено' in t.get('status', '')])

        summary_text = f"Итого: {total_count} транзакций, из них {completed} выполнено"
        summary_para = Paragraph(summary_text, normal_style)
        elements.append(summary_para)

        # Примечание
        note_text = "Отчет сгенерирован автоматически системой Crypto Wallet"
        note_style = ParagraphStyle(
            'Note',
            parent=styles['Normal'],
            fontName=normal_font,
            fontSize=8,
            textColor=colors.grey
        )
        elements.append(Paragraph(note_text, note_style))

        # Строим PDF
        doc.build(elements)

        return output_file