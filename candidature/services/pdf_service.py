import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from .qr_code_service import generate_qr_code_image


def generate_convocation_pdf(convocation):
    """
    Génère un document PDF professionnel contenant les détails de la convocation
    à la Réunion d'Information (RI) et le QR code unique du candidat.
    """
    buffer = io.BytesIO()

    # Document A4 avec marges équilibrées
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Styles personnalisés
    header_style = ParagraphStyle(
        "BrandHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#D20C4F"),
        alignment=1,  # Centré
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#00313C"),
        alignment=1,
    )

    label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#00313C"),
    )

    value_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1F2937"),
    )

    instruction_style = ParagraphStyle(
        "Instruction",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#D20C4F"),
        alignment=1,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6B7280"),
        alignment=1,
    )

    elements = []

    # 1. En-tête de la marque
    elements.append(Paragraph("SOURCING HUB", header_style))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("CONVOCATION À LA RÉUNION D'INFORMATION", subtitle_style))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#E2E8F0"), spaceAfter=15))

    # 2. Informations de la candidature et de la convocation
    candidature = convocation.candidature
    if hasattr(convocation, "reunion_information"):
        ri = convocation.reunion_information
        campagne = ri.campagne
        date_obj = ri.date
        lieu_str = ri.lieu
        token_val = convocation.token
        if convocation.creneau:
            groupe_nom = convocation.creneau.nom or "Créneau"
            h_deb = str(convocation.creneau.heure_debut)[:5]
            h_fin = f" - {str(convocation.creneau.heure_fin)[:5]}" if convocation.creneau.heure_fin else ""
            heure_str = f"{h_deb}{h_fin}"
            if convocation.creneau.nom:
                groupe_str = f"{convocation.creneau.nom} ({heure_str})"
            else:
                groupe_str = heure_str
        else:
            groupe_str = "Standard"
            heure_str = "Selon planning"
    else:
        campagne = convocation.campagne
        date_obj = convocation.date
        lieu_str = getattr(convocation, "lieu", "Simplon Sénégal")
        token_val = getattr(convocation, "qr_token", candidature.qr_token)
        h_deb = str(convocation.heure_debut)[:5]
        h_fin = f" - {str(convocation.heure_fin)[:5]}" if convocation.heure_fin else ""
        heure_str = f"{h_deb}{h_fin}"
        groupe_str = heure_str

    date_str = date_obj.strftime("%d/%m/%Y") if hasattr(date_obj, "strftime") else str(date_obj)

    table_data = [
        [
            Paragraph("Nom :", label_style),
            Paragraph(candidature.nom.upper(), value_style),
        ],
        [
            Paragraph("Prénom :", label_style),
            Paragraph(candidature.prenom, value_style),
        ],
        [
            Paragraph("Campagne :", label_style),
            Paragraph(campagne.title, value_style),
        ],
        [
            Paragraph("Date :", label_style),
            Paragraph(date_str, value_style),
        ],
        [
            Paragraph("Groupe / Horaire :", label_style),
            Paragraph(groupe_str, value_style),
        ],
        [
            Paragraph("Lieu :", label_style),
            Paragraph(lieu_str, value_style),
        ],
    ]

    info_table = Table(table_data, colWidths=[4 * cm, 11 * cm])
    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elements.append(info_table)
    elements.append(Spacer(1, 0.8 * cm))

    # 3. QR Code unique
    qr_img = generate_qr_code_image(token_val)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Image de taille 5cm x 5cm
    qr_flowable = Image(qr_buffer, width=5.5 * cm, height=5.5 * cm)
    qr_flowable.hAlign = "CENTER"
    elements.append(qr_flowable)
    elements.append(Spacer(1, 0.4 * cm))

    # 4. Consigne de présentation
    elements.append(
        Paragraph("Veuillez présenter ce QR code à l'administrateur à votre arrivée.", instruction_style)
    )
    elements.append(Spacer(1, 0.8 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=10))

    # 5. Pied de page
    elements.append(
        Paragraph("Ce document est personnel et servira d'identification lors de la réunion d'information.", footer_style)
    )

    doc.build(elements)
    return buffer.getvalue()
