import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_order_invoice_pdf(order, vendor):
    """Build a simple, clean invoice/receipt PDF for a regular Order and
    return it as an in-memory BytesIO buffer ready to send to the client."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=24 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#5E1836")
    )
    heading_style = ParagraphStyle(
        "InvoiceHeading", parent=styles["Heading3"], textColor=colors.HexColor("#5E1836")
    )
    normal = styles["Normal"]

    story = []
    story.append(Paragraph(vendor.business_name, title_style))
    if vendor.tagline:
        story.append(Paragraph(vendor.tagline, normal))
    story.append(Spacer(1, 6))
    contact_bits = [b for b in [vendor.phone_number, vendor.contact_email, vendor.address] if b]
    if contact_bits:
        story.append(Paragraph(" | ".join(contact_bits), normal))
    story.append(Spacer(1, 18))

    story.append(Paragraph(f"Order Receipt — #{order.order_code}", heading_style))
    story.append(Spacer(1, 8))

    info_table = Table(
        [
            ["Order Date:", order.created_at.strftime("%d %b %Y")],
            ["Order Status:", order.status],
            ["Customer Name:", order.customer_name],
            ["Phone:", order.phone],
            ["Delivery Address:", order.address or "—"],
        ],
        colWidths=[130, 340],
    )
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5E1836")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    unit_price = float(order.total_price) + float(order.discount_amount or 0)
    unit_price = unit_price / order.quantity if order.quantity else unit_price

    items_data = [["Item", "Qty", "Unit Price", "Amount"]]
    items_data.append([
        order.product.name, str(order.quantity),
        f"Rs. {unit_price:,.2f}", f"Rs. {float(unit_price) * order.quantity:,.2f}",
    ])

    items_table = Table(items_data, colWidths=[230, 60, 90, 90])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5E1836")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0D3D8")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    totals_data = []
    if order.discount_amount:
        totals_data.append(["Coupon Applied:", order.coupon_code or "—"])
        totals_data.append(["Discount:", f"- Rs. {float(order.discount_amount):,.2f}"])
    totals_data.append(["Total Amount:", f"Rs. {float(order.total_price):,.2f}"])

    totals_table = Table(totals_data, colWidths=[380, 90])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for shopping with us!", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_custom_order_invoice_pdf(custom_order, vendor):
    """Build a receipt PDF for a CustomOrder (no fixed price, so it lists the
    requested specs instead of a price table)."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=24 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#5E1836")
    )
    heading_style = ParagraphStyle(
        "InvoiceHeading", parent=styles["Heading3"], textColor=colors.HexColor("#5E1836")
    )
    normal = styles["Normal"]

    story = [Paragraph(vendor.business_name, title_style), Spacer(1, 6)]
    contact_bits = [b for b in [vendor.phone_number, vendor.contact_email, vendor.address] if b]
    if contact_bits:
        story.append(Paragraph(" | ".join(contact_bits), normal))
    story.append(Spacer(1, 18))
    story.append(Paragraph(f"Custom Order Receipt — #{custom_order.order_code}", heading_style))
    story.append(Spacer(1, 8))

    rows = [
        ["Order Date:", custom_order.created_at.strftime("%d %b %Y")],
        ["Status:", custom_order.status],
        ["Customer Name:", custom_order.full_name],
        ["Mobile:", custom_order.mobile],
        ["Item Type:", custom_order.item_type],
        ["Preferred Colours:", custom_order.preferred_colours or "—"],
        ["Size:", custom_order.size or "—"],
        ["Quantity:", str(custom_order.quantity)],
        ["Required By:", custom_order.required_date or "—"],
        ["Design Requirements:", custom_order.design_requirements or "—"],
    ]
    table = Table(rows, colWidths=[150, 320])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5E1836")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0D3D8")),
    ]))
    story.append(table)
    story.append(Spacer(1, 24))
    story.append(Paragraph("This is a custom order request — final pricing will be confirmed by the seller.", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer
