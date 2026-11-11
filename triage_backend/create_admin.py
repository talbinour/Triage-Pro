"""
Script à exécuter UNE SEULE FOIS pour créer le premier compte admin.
Lancez : python create_admin.py
(depuis le dossier triage_backend, avec le venv activé)
"""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'triage_backend.settings')

import django
django.setup()

from triage.mongo_service import find_infirmier_by_email, create_infirmier
from triage.auth_utils import hash_password

email = 'admin@hopital.fr'

if find_infirmier_by_email(email):
    print(f"⚠️  Un compte avec l'email {email} existe déjà.")
else:
    create_infirmier({
        'email': email,
        'nom': 'Admin',
        'prenom': 'Super',
        'password': hash_password('Admin1234!'),
        'role': 'admin',
        'statut': 'actif',
        'telephone': '',
        'service': 'Administration',
    })
    print("✅ Compte admin créé avec succès !")
    print(f"   Email    : {email}")
    print(f"   Password : Admin1234!")
    print(f"   Rôle     : admin")