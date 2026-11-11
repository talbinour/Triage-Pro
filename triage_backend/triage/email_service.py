"""
email_service.py — Envoi d'emails avec QR code
Placez ce fichier dans : triage_backend/triage/email_service.py
"""
import smtplib
import qrcode
import io
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from django.conf import settings


def generer_qr_code(qr_token: str) -> tuple[bytes, str]:
    """
    Génère un QR code contenant le token de connexion.
    Retourne : (bytes PNG, string base64)
    """
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    # Le QR code encode l'URL de connexion automatique
    qr_data = f"{settings.FRONTEND_URL}/auth/qr-login?token={qr_token}"
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#09637E", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()
    base64_str = base64.b64encode(png_bytes).decode('utf-8')
    return png_bytes, base64_str


def envoyer_email_bienvenue(infirmier: dict, password_clair: str, qr_token: str) -> bool:
    """
    Envoie un email de bienvenue avec les identifiants et le QR code.
    Retourne True si succès, False sinon.
    """
    try:
        # Générer le QR code
        qr_bytes, _ = generer_qr_code(qr_token)

        # Construire l'email
        msg = MIMEMultipart('related')
        msg['Subject'] = f"Bienvenue sur TriagePro — Vos identifiants de connexion"
        msg['From'] = f"TriagePro <{settings.EMAIL_HOST_USER}>"
        msg['To'] = infirmier['email']

        # Corps HTML
        html = _construire_html(infirmier, password_clair, qr_token)
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        # Attacher le QR code comme image inline
        qr_image = MIMEImage(qr_bytes, name='qrcode.png')
        qr_image.add_header('Content-ID', '<qrcode>')
        qr_image.add_header('Content-Disposition', 'inline', filename='qrcode.png')
        msg.attach(qr_image)

        # Envoi SMTP
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            if settings.EMAIL_USE_TLS:
                server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, infirmier['email'], msg.as_string())

        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def _construire_html(infirmier: dict, password_clair: str, qr_token: str) -> str:
    nom_complet = f"{infirmier.get('prenom', '')} {infirmier.get('nom', '')}"
    role_label = "Administrateur" if infirmier.get('role') == 'admin' else "Infirmier(ère)"
    service = infirmier.get('service', '') or 'Non défini'
    frontend_url = settings.FRONTEND_URL

    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background:#EBF4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#EBF4F6;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#09637E,#088395);border-radius:16px 16px 0 0;padding:36px 40px;text-align:center;">
            <div style="font-size:32px;margin-bottom:8px;">🏥</div>
            <h1 style="color:white;margin:0;font-size:26px;font-weight:800;letter-spacing:-0.5px;">TriagePro</h1>
            <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:14px;">Système de triage médical</p>
          </td>
        </tr>

        <!-- Corps -->
        <tr>
          <td style="background:white;padding:40px;">

            <p style="color:#09637E;font-size:16px;font-weight:600;margin:0 0 8px;">Bonjour {nom_complet},</p>
            <p style="color:#4a6a75;font-size:15px;line-height:1.6;margin:0 0 28px;">
              Votre compte <strong>TriagePro</strong> a été créé avec succès.
              Vous trouverez ci-dessous vos identifiants de connexion ainsi que votre QR code personnel.
            </p>

            <!-- Identifiants -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#EBF4F6;border-radius:12px;padding:24px;margin-bottom:28px;border-left:4px solid #09637E;">
              <tr><td>
                <p style="color:#09637E;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 16px;">Vos identifiants</p>
                <table width="100%">
                  <tr>
                    <td style="color:#5a8a96;font-size:13px;padding:6px 0;width:140px;">📧 Email</td>
                    <td style="color:#0d2e38;font-size:14px;font-weight:600;">{infirmier['email']}</td>
                  </tr>
                  <tr>
                    <td style="color:#5a8a96;font-size:13px;padding:6px 0;">🔐 Mot de passe</td>
                    <td style="color:#0d2e38;font-size:14px;font-weight:600;font-family:monospace;background:#fff;padding:4px 10px;border-radius:6px;border:1px solid #c5dde3;">{password_clair}</td>
                  </tr>
                  <tr>
                    <td style="color:#5a8a96;font-size:13px;padding:6px 0;">👤 Rôle</td>
                    <td style="color:#0d2e38;font-size:14px;font-weight:600;">{role_label}</td>
                  </tr>
                  <tr>
                    <td style="color:#5a8a96;font-size:13px;padding:6px 0;">🏥 Service</td>
                    <td style="color:#0d2e38;font-size:14px;font-weight:600;">{service}</td>
                  </tr>
                </table>
              </td></tr>
            </table>

            <!-- QR Code -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fdfе;border:1.5px dashed #7AB2B2;border-radius:12px;padding:28px;margin-bottom:28px;text-align:center;">
              <tr><td>
                <p style="color:#09637E;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 16px;">📱 Votre QR Code de connexion</p>
                <img src="cid:qrcode" width="180" height="180" style="border-radius:12px;border:3px solid #EBF4F6;" alt="QR Code"/>
                <p style="color:#5a8a96;font-size:13px;margin:16px 0 0;line-height:1.5;">
                  Scannez ce code depuis l'application mobile TriagePro<br/>
                  pour vous connecter instantanément sans saisir vos identifiants.
                </p>
              </td></tr>
            </table>

            <!-- Bouton -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td align="center">
                <a href="{frontend_url}/login" style="display:inline-block;background:linear-gradient(135deg,#09637E,#088395);color:white;text-decoration:none;padding:14px 32px;border-radius:10px;font-size:15px;font-weight:700;letter-spacing:0.3px;">
                  Accéder à TriagePro →
                </a>
              </td></tr>
            </table>

            <p style="color:#e67e22;font-size:13px;background:#fef9e7;border-radius:8px;padding:12px 16px;margin:28px 0 0;border-left:3px solid #e67e22;">
              ⚠️ Pour votre sécurité ne partagez jamais votre QR code.
            </p>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#09637E;border-radius:0 0 16px 16px;padding:20px 40px;text-align:center;">
            <p style="color:rgba(255,255,255,0.7);font-size:12px;margin:0;">
              © 2026 TriagePro · Système de triage médical · Email automatique, ne pas répondre
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>
"""