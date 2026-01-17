import json
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from textwrap import wrap

def sanitize_path(path: str) -> str:
    path = path.replace("\\", "/")
    path = path.lstrip("/")

    components = path.split("/")

    sanitized_components = [component for component in components if component not in ("..", ".")]
    return "/".join(sanitized_components) if sanitized_components else "/"

def is_valid_json(file):
        try:
            json.load(file)
            file.seek(0)
            return True
        except Exception:
            return False

def create_invoice_pdf(order):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    pdfmetrics.registerFont(TTFont("Helvetica", "Helvetica.ttf"))
    pdfmetrics.registerFont(TTFont("Helvetica-Bold", "Helvetica-Bold.ttf"))

    main_color = colors.HexColor("#326442")

    logo_path = "uploads/Logo.jpg"
    c.drawImage(logo_path, 30, 750, height=70, width=150)
    c.setStrokeColor(main_color)
    c.setLineWidth(2)
    c.line(30, 745, 580, 745)

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(main_color)
    c.drawString(460, 750, "RECHNUNG")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(400, 680, f"Datum: {order['date']}")
    c.drawString(400, 665, f"Rechnung Nr.: {order['id']}")
    c.drawString(400, 650, f"Fällig: {(datetime.strptime(order['date'], '%d.%m.%Y') + timedelta(days=7)).strftime('%d.%m.%Y')}")

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(main_color)
    c.drawString(100, 680, "Rechnungsempfänger:")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(100, 665, f"{order['name']}")
    c.drawString(100, 650, f"{order['address']}")
    c.drawString(100, 635, f"{order['zip_code']} {order['city']}")
    c.drawString(100, 620, f"{order['country']}")

    c.setFillColor(main_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 580, "Nr.")
    c.drawString(90, 580, "Artikelbezeichnung")
    c.drawString(230, 580, "Menge")
    c.drawString(290, 580, "Preis/Stk.")
    c.drawString(370, 580, "USt. %")
    c.drawString(430, 580, "USt. Betrag")
    c.drawString(510, 580, "Betrag")
    c.setLineWidth(1)
    c.line(30, 575, 580, 575)

    y_position = 560
    for pos, item in enumerate(order['items'], start=1):
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(50, y_position, str(pos))
        c.drawString(240, y_position, str(item['quantity']))
        c.drawString(290, y_position, f"€ {item['unit_price']:,.2f}")
        c.drawString(375, y_position, f"{int(item['tax_rate'] * 100)}%")
        c.drawString(430, y_position, f"€ {item['unit_price']*item['tax_rate']*item['quantity']:,.2f}")
        c.drawString(510, y_position, f"€ {item['total']:,.2f}")

        item_name_wrapped = wrap(item["name"], width=25)

        for line in item_name_wrapped:
            c.drawString(90, y_position, line)
            y_position -= 12
            
        c.setLineWidth(0.5)
        c.line(30, y_position, 580, y_position)
        y_position -= 15

    y_position -= 40
    c.setLineWidth(1)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(350, y_position, "Zwischensumme:")
    c.drawString(480, y_position, f"€ {order['old_total']:,.2f}")
    y_position -= 15
    c.drawString(350, y_position, "Rabatt:")
    c.drawString(480, y_position, f"€ {round(order['discount'], 2):,.2f}")
    y_position -= 5
    c.line(350, y_position, 550, y_position)
    y_position -= 15
    c.drawString(350, y_position, "Enpreis:")
    c.drawString(480, y_position, f"€ {round(order['total_price']/1.2, 2):,.2f}")
    y_position -= 15
    c.drawString(350, y_position, "inkl. 20% USt.:")
    c.drawString(480, y_position, f"€ {order['total_tax']:,.2f}")
    y_position -= 15
    c.drawString(350, y_position, "Nettobetrag:")
    c.drawString(480, y_position, f"€ {round(order['total_price']/1.2, 2):,.2f}")
    y_position -= 5
    c.line(350, y_position, 550, y_position)
    y_position -= 15
    c.setFont("Helvetica-Bold", 14)
    c.drawString(350, y_position, "Gesamtbetrag:")
    c.drawString(480, y_position, f"€ {order['total_price']:,.2f}")

    y_position = 150
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(main_color)
    c.drawString(30, y_position, "Zahlungsbedingungen:")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(30, y_position - 10, "Bitte überweisen Sie den fälligen Gesamtbetrag bis spätestens 7 Tage nach Erhalt der Rechnung")
    c.drawString(30, y_position - 20, "auf folgendes Konto: ATXX XXX XXXX XXXX. Zahlungsreferenz: FFFFFFFFFFFFFFFFFFFFFFFFFFFFf",)

    y_position -= 50
    c.setLineWidth(10)
    c.line(30, y_position, 580, y_position)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    y_position -= 15
    c.drawString(50, y_position, "Birdie Club GmbH")
    c.drawString(50, y_position - 10, "Polgarstraße 24")
    c.drawString(50, y_position - 20, "1220 Wien")
    c.drawString(50, y_position - 30, "Österreich")
    c.drawString(350, y_position, "Kontaktinformation:")
    c.drawString(350, y_position - 10, "E-Mail: birdie2943@uebungsfirmen.at")
    c.drawString(350, y_position - 20, "Website: http://")

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer