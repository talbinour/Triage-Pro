"""
qr_auth_service.py — Gestion des tokens QR

"""
import secrets
from datetime import datetime
from .mongo_service import infirmier_collection, find_infirmier_by_id


def generer_qr_token() -> str:
    """Génère un token unique et sécurisé pour le QR code"""
    return secrets.token_urlsafe(32)


def sauvegarder_qr_token(infirmier_id: str, qr_token: str, qr_base64: str):
    """Sauvegarde le token QR et l'image base64 dans MongoDB"""
    infirmier_collection().update_one(
        {'_id': __import__('bson').ObjectId(infirmier_id)},
        {'$set': {
            'qr_token': qr_token,
            'qr_code_base64': qr_base64,
            'qr_genere_le': datetime.utcnow(),
        }}
    )


def valider_qr_token(qr_token: str) -> dict | None:
    """
    Vérifie si un QR token est valide et retourne l'infirmier correspondant.
    Retourne None si invalide.
    """
    if not qr_token:
        return None
    user = infirmier_collection().find_one({
        'qr_token': qr_token,
        'statut': 'actif'
    })
    return user