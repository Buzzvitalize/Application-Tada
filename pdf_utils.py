from io import BytesIO
from fpdf import FPDF
from uuid import uuid4
import os
from flask import current_app
try:
    import qrcode
except ModuleNotFoundError:  # pragma: no cover
    qrcode = None

ITBIS_RATE = 0.18


def _fmt_money(value):
    return f"RD${value:,.2f}"


def generate_pdf(title, company, client, items, subtotal, itbis, total,
                 ncf=None, seller=None, payment_method=None, bank=None,
                 order_number=None, doc_number=None, invoice_type=None,
                 note=None, output_path=None, qr_url=None,
                 date=None, valid_until=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    primary = (30, 58, 138)

    if company.get('logo'):
        pdf.image(company['logo'], 10, 10, 25)
        info_x = 40
    else:
        info_x = 10

    pdf.set_xy(info_x, 10)
    pdf.set_text_color(*primary)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(100, 6, company['name'], ln=1)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(info_x)
    pdf.cell(100, 5, company['address'], ln=1)
    pdf.set_x(info_x)
    pdf.cell(100, 5, f"RNC: {company['rnc']} Tel: {company['phone']}", ln=1)
    if company.get('website'):
        pdf.set_x(info_x)
        pdf.cell(100, 5, company['website'], ln=1)

    header_x = 150
    pdf.set_xy(header_x, 10)
    pdf.set_text_color(*primary)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(50, 8, title.upper(), align='R', ln=1)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    if doc_number is not None:
        pdf.set_xy(header_x, 18)
        pdf.cell(50, 5, f"No.: {doc_number:04d}", align='R', ln=1)
    if date:
        pdf.set_xy(header_x, 24)
        pdf.cell(50, 5, date.strftime('%d/%m/%Y %I:%M %p'), align='R', ln=1)
    if valid_until:
        pdf.set_xy(header_x, 30)
        pdf.cell(50, 5, f"Válida hasta: {valid_until.strftime('%d/%m/%Y')}", align='R', ln=1)
    if ncf:
        pdf.set_xy(header_x, 36)
        pdf.cell(50, 5, f"NCF: {ncf}", align='R', ln=1)
    if invoice_type:
        pdf.set_xy(header_x, 42)
        pdf.cell(50, 5, f"Tipo: {invoice_type}", align='R', ln=1)
    if order_number is not None:
        pdf.set_xy(header_x, 48)
        pdf.cell(50, 5, f"Pedido #{order_number:04d}", align='R', ln=1)

    pdf.set_y(60)
    pdf.set_font('Helvetica', '', 12)
    full_name = f"{client.name} {client.last_name}".strip() if getattr(client, 'last_name', None) else client.name
    pdf.cell(0, 6, f"Cliente: {full_name}", ln=1)
    if client.identifier:
        pdf.cell(0, 6, f"Cédula/RNC: {client.identifier}", ln=1)
    if client.phone:
        pdf.cell(0, 6, f"Teléfono: {client.phone}", ln=1)
    if client.street or client.sector or client.province:
        pdf.cell(0, 6, f"Dirección: {client.street or ''}, {client.sector or ''}, {client.province or ''}", ln=1)
    if client.email:
        pdf.cell(0, 6, f"Email: {client.email}", ln=1)
    pdf.ln(5)

    pdf.set_font('Helvetica', 'B', 12)
    col_code = 20
    col_ref = 20
    col_name = 45
    col_unit = 15
    col_price = 25
    col_qty = 15
    col_discount = 25
    col_total = 30
    table_width = (col_code + col_ref + col_name + col_unit +
                   col_price + col_qty + col_discount + col_total)
    table_x = (pdf.w - table_width) / 2
    pdf.set_fill_color(*primary)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(table_x)
    pdf.cell(col_code, 8, 'Código', border=1, align='C', fill=True)
    pdf.cell(col_ref, 8, 'Ref.', border=1, align='C', fill=True)
    pdf.cell(col_name, 8, 'Producto', border=1, align='C', fill=True)
    pdf.cell(col_unit, 8, 'Unidad', border=1, align='C', fill=True)
    pdf.cell(col_price, 8, 'Precio', border=1, align='R', fill=True)
    pdf.cell(col_qty, 8, 'Cant.', border=1, align='R', fill=True)
    pdf.cell(col_discount, 8, 'Desc.', border=1, align='R', fill=True)
    pdf.cell(col_total, 8, 'Total', border=1, ln=1, align='R', fill=True)

    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for i in items:
        total_line = (i.unit_price * i.quantity) - i.discount
        pdf.set_x(table_x)
        if fill:
            pdf.set_fill_color(249, 250, 251)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_code, 8, getattr(i, 'code', '') or '', border=1, fill=True)
        pdf.cell(col_ref, 8, getattr(i, 'reference', '') or '', border=1, fill=True)
        pdf.cell(col_name, 8, i.product_name, border=1, fill=True)
        pdf.cell(col_unit, 8, i.unit, border=1, align='C', fill=True)
        pdf.cell(col_price, 8, _fmt_money(i.unit_price), border=1, align='R', fill=True)
        pdf.cell(col_qty, 8, str(i.quantity), border=1, align='R', fill=True)
        pdf.cell(col_discount, 8, _fmt_money(i.discount), border=1, align='R', fill=True)
        pdf.cell(col_total, 8, _fmt_money(total_line), border=1, ln=1, align='R', fill=True)
        fill = not fill

    discount_total = sum(i.discount for i in items)
    pdf.ln(5)
    pdf.set_x(table_x)
    pdf.set_draw_color(200, 200, 200)
    last_col = col_total
    pdf.cell(table_width - last_col, 8, 'Subtotal', border='LT', align='R')
    pdf.cell(last_col, 8, _fmt_money(subtotal), border='TR', ln=1, align='R')
    pdf.set_x(table_x)
    pdf.cell(table_width - last_col, 8, f"ITBIS ({ITBIS_RATE*100:.0f}%)", border='L', align='R')
    pdf.cell(last_col, 8, _fmt_money(itbis), border='R', ln=1, align='R')
    pdf.set_x(table_x)
    pdf.cell(table_width - last_col, 8, 'Descuento', border='L', align='R')
    pdf.cell(last_col, 8, _fmt_money(discount_total), border='R', ln=1, align='R')
    pdf.set_x(table_x)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(table_width - last_col, 8, 'Total', border='LB', align='R')
    pdf.cell(last_col, 8, _fmt_money(total), border='RB', ln=1, align='R')

    if seller or payment_method:
        pdf.ln(5)
        if seller:
            pdf.cell(0, 6, f"Vendedor: {seller}", ln=1)
        if payment_method:
            method = payment_method
            if payment_method.lower().startswith('transfer') and bank:
                method += f" - {bank}"
            pdf.cell(0, 6, f"Método de pago: {method}", ln=1)

    if note:
        pdf.ln(5)
        pdf.multi_cell(0, 6, f"Nota: {note}")

    if qr_url and qrcode:
        os.makedirs(os.path.join(current_app.static_folder, 'qrcodes'), exist_ok=True)
        qr_path = os.path.join(current_app.static_folder, 'qrcodes', f"{uuid4().hex}.png")
        img = qrcode.make(qr_url)
        img.save(qr_path)
        pdf.image(qr_path, x=170, y=260, w=30)

    if output_path:
        pdf.output(output_path)
        return output_path
    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output
