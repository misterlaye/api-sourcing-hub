import io
import base64
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_qr_code_image(qr_token):
    """
    Génère l'image PIL d'un QR code contenant UNIQUEMENT le token sécurisé.
    Aucune information personnelle (nom, email, téléphone) n'est injectée dans le QR code.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(str(qr_token))
    qr.make(fit=True)
    return qr.make_image(fill_color="#00313C", back_color="white")


def generate_qr_code_bytes(qr_token):
    """
    Retourne les octets (PNG) de l'image QR code.
    """
    img = generate_qr_code_image(qr_token)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_code_base64(qr_token):
    """
    Retourne le QR code sous forme de chaîne Data URL Base64 (utile pour le rendu web ou inline).
    """
    raw_bytes = generate_qr_code_bytes(qr_token)
    b64 = base64.b64encode(raw_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"
