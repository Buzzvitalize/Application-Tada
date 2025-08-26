"""PDF generation using WeasyPrint with modern invoice style."""
from __future__ import annotations

from weasyprint import HTML
from datetime import datetime
from pathlib import Path

BLUE = "#1e3a8a"

STYLE = f"""
@page {{
    size: A4;
    margin: 2cm;
}}
body {{ font-family: Helvetica, Arial, sans-serif; margin:0; }}
.header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:4px solid {BLUE}; padding-bottom:10px; margin-bottom:20px; }}
.logo {{ width:120px; }}
h1 {{ color:{BLUE}; margin:0; font-size:28px; }}
.meta {{ text-align:right; font-size:14px; }}
.two-col {{ display:flex; justify-content:space-between; margin-bottom:20px; }}
.box {{ width:48%; font-size:14px; }}
table {{ width:100%; border-collapse:collapse; margin-bottom:20px; font-size:14px; }}
th {{ background:{BLUE}; color:white; padding:8px; text-align:left; }}
td {{ padding:8px; border-bottom:1px solid #e5e7eb; }}
tr:nth-child(even) td {{ background:#f9fafb; }}
.totals {{ width:40%; margin-left:auto; }}
.totals td {{ padding:4px 8px; }}
.totals tr:last-child td {{ font-size:16px; font-weight:bold; color:{BLUE}; border-top:2px solid {BLUE}; }}
.notes {{ margin-top:40px; font-size:12px; }}
"""


def _fmt_currency(value: float) -> str:
    """Return a Dominican peso string with thousands separator."""
    return f"RD$ {value:,.2f}"


def build_html(data: dict) -> str:
    rows = "".join(
        f"<tr><td>{i['code']}</td><td>{i['name']}</td><td>{i['unit']}</td><td>{_fmt_currency(i['price'])}</td><td>{i['qty']}</td><td>{i.get('discount',0)}%</td><td>{_fmt_currency(i['total'])}</td></tr>"  # noqa: E501
        for i in data['items']
    )
    return f"""
<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='utf-8'>
<style>{STYLE}</style>
</head>
<body>
<div class='header'>
  <img src='{data['company']['logo']}' class='logo'>
  <h1>Factura</h1>
  <div class='meta'>
    <div>N\u00b0 {data['number']}</div>
    <div>{data.get('date', datetime.now().strftime('%d/%m/%Y'))}</div>
  </div>
</div>
<div class='two-col'>
  <div class='box'>
    <strong>{data['company']['name']}</strong><br>
    {data['company']['address']}<br>
    {data['company']['phone']}
  </div>
  <div class='box'>
    <strong>{data['client']['name']}</strong><br>
    {data['client']['address']}<br>
    {data['client']['phone']}
  </div>
</div>
<table>
  <thead>
    <tr>
      <th>Código</th><th>Producto</th><th>Unidad</th><th>Precio</th><th>Cant.</th><th>Desc.</th><th>Total</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<table class='totals'>
  <tr><td>Subtotal</td><td style='text-align:right'>{_fmt_currency(data['subtotal'])}</td></tr>
  <tr><td>ITBIS (18%)</td><td style='text-align:right'>{_fmt_currency(data['tax'])}</td></tr>
  <tr><td>Total</td><td style='text-align:right'>{_fmt_currency(data['total'])}</td></tr>
</table>
<div class='notes'>Gracias por su compra</div>
</body>
</html>
"""


def generate_invoice_pdf(data: dict, output_path: str | Path) -> None:
    """Generate a PDF invoice using WeasyPrint."""
    html = build_html(data)
    HTML(string=html, base_url='.').write_pdf(output_path)


if __name__ == '__main__':
    sample = {
        'number': 'F-001',
        'date': datetime.now().strftime('%d/%m/%Y'),
        'company': {
            'name': 'Tiendix SRL',
            'address': 'Av. Principal 123, Santo Domingo',
            'phone': '+1 809-555-0000',
            'logo': 'static/pos.svg',
        },
        'client': {
            'name': 'Juan Pérez',
            'address': 'Calle 1, SD',
            'phone': '809-000-0000',
        },
        'items': [
            {'code': 'P001', 'name': 'Servicio A', 'unit': 'und', 'price': 1500, 'qty': 2, 'total': 3000},
            {'code': 'P002', 'name': 'Producto B', 'unit': 'kg', 'price': 500, 'qty': 4, 'discount': 5, 'total': 1900},
        ],
        'subtotal': 4900,
        'tax': 882,
        'total': 5782,
    }
    generate_invoice_pdf(sample, 'factura_weasy.pdf')
    print('factura_weasy.pdf generated')
