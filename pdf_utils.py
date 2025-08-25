from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from uuid import uuid4
import qrcode
import os
from flask import current_app

ITBIS_RATE = 0.18


def _fmt_money(value):
    return f"RD${value:,.2f}"


def generate_pdf(title, company, client, items, subtotal, itbis, total,
                 ncf=None, seller=None, payment_method=None, bank=None,
                 order_number=None, doc_number=None, invoice_type=None,
                 note=None, output_path=None, qr_url=None,
                 date=None, valid_until=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    elements = []
    styles = getSampleStyleSheet()
    primary = colors.HexColor('#1e3a8a')

    logo = Image(company['logo'], width=1.2 * inch, height=1.2 * inch) if company.get('logo') else ''
    comp_info = f"<b>{company['name']}</b><br/>{company['address']}<br/>RNC: {company['rnc']} Tel: {company['phone']}"
    if company.get('website'):
        comp_info += f"<br/>{company['website']}"
    comp_para = Paragraph(comp_info, styles['Normal'])
    meta = f"<b>{title}</b><br/>"
    if doc_number is not None:
        meta += f"No.: {doc_number:04d}<br/>"
    if date:
        meta += date.strftime('%d/%m/%Y %I:%M %p') + '<br/>'
    if valid_until:
        meta += f"Válida hasta: {valid_until.strftime('%d/%m/%Y')}<br/>"
    if ncf:
        meta += f"NCF: {ncf}<br/>"
    if invoice_type:
        meta += f"Tipo: {invoice_type}<br/>"
    if order_number is not None:
        meta += f"Pedido #{order_number:04d}<br/>"
    meta_para = Paragraph(meta, styles['Normal'])
    header = Table([[logo, comp_para, meta_para]], colWidths=[1.5 * inch, 3.5 * inch, 2.5 * inch])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 12))

    full_name = f"{client.name} {getattr(client, 'last_name', '')}".strip()
    cli_info = f"<b>Cliente:</b> {full_name}<br/>"
    if client.identifier:
        cli_info += f"<b>Cédula/RNC:</b> {client.identifier}<br/>"
    if client.phone:
        cli_info += f"<b>Teléfono:</b> {client.phone}<br/>"
    if client.street or client.sector or client.province:
        cli_info += f"<b>Dirección:</b> {client.street or ''}, {client.sector or ''}, {client.province or ''}<br/>"
    if client.email:
        cli_info += f"<b>Email:</b> {client.email}<br/>"
    elements.append(Paragraph(cli_info, styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [['Código', 'Ref.', 'Producto', 'Unidad', 'Precio', 'Cant.', 'Desc.', 'Total']]
    for i in items:
        total_line = (i.unit_price * i.quantity) - i.discount
        data.append([
            getattr(i, 'code', '') or '',
            getattr(i, 'reference', '') or '',
            i.product_name,
            i.unit,
            _fmt_money(i.unit_price),
            str(i.quantity),
            _fmt_money(i.discount),
            _fmt_money(total_line),
        ])
    table = Table(data, colWidths=[55, 50, 150, 50, 60, 40, 60, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    elements.append(table)

    discount_total = sum(i.discount for i in items)
    totals = [
        ['Subtotal', _fmt_money(subtotal)],
        [f"ITBIS ({ITBIS_RATE*100:.0f}%)", _fmt_money(itbis)],
        ['Descuento', _fmt_money(discount_total)],
        ['Total', _fmt_money(total)],
    ]
    totals_table = Table(totals, colWidths=[395, 80])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), primary),
    ]))
    elements.append(Spacer(1, 12))
    elements.append(totals_table)

    extras = []
    if seller:
        extras.append(f"Vendedor: {seller}")
    if payment_method:
        method = payment_method
        if payment_method.lower().startswith('transfer') and bank:
            method += f" - {bank}"
        extras.append(f"Método de pago: {method}")
    if note:
        extras.append(f"Nota: {note}")
    for line in extras:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(line, styles['Normal']))

    if qr_url:
        os.makedirs(os.path.join(current_app.static_folder, 'qrcodes'), exist_ok=True)
        qr_path = os.path.join(current_app.static_folder, 'qrcodes', f"{uuid4().hex}.png")
        qrcode.make(qr_url).save(qr_path)
        elements.append(Spacer(1, 12))
        elements.append(Image(qr_path, width=1.2 * inch, height=1.2 * inch))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        return output_path
    buffer.seek(0)
    return buffer

