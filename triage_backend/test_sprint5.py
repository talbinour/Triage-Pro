# test_sprint5.py — à placer dans triage_backend/
import os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'triage_backend.settings'

import django
django.setup()

# Test lits
from triage.lit_service import initialiser_lits_defaut, get_resume_lits
initialiser_lits_defaut()
print("── Lits ──")
for r in get_resume_lits():
    print(f"  {r['type']:15s} → {r['libres']}/{r['total']} libres")

# Test équipements
from triage.equipement_service import initialiser_equipements_defaut, get_tous_equipements, serialize_equipement
initialiser_equipements_defaut()
print("\n── Équipements ──")
for eq in get_tous_equipements():
    s = serialize_equipement(eq)
    print(f"  {s['nom']:25s} → {s['disponible']}/{s['total']} {s['unite']}")

# Test comptage patients
from triage.patient_service import compter_patients_par_niveau
print(f"\n── Patients en attente : {compter_patients_par_niveau()}")

print("\n✓ Étape 1 complète !")

# ── Test alertes (ajoutez à la fin de test_sprint5.py) ──
print("\n── Test alertes ──")
from triage.alerte_service import analyser_situation, get_dashboard_data

alertes = analyser_situation()
for a in alertes:
    icone = {'critique': '🔴', 'avertissement': '🟠', 'info': '🔵'}
    print(f"  {icone.get(a['severite'], '⚪')} [{a['severite'].upper():14s}] {a['message']}")
    print(f"     {a['details']}")

print("\n── Test dashboard complet ──")
data = get_dashboard_data()
print(f"  Patients en attente  : {data['patients']['total_attente']}")
print(f"  En consultation      : {data['patients']['en_consultation']}")
print(f"  Infirmiers en service: {data['personnel']['en_service']}")
print(f"  Alertes générées     : {len(data['alertes'])}")

print("\n✓ Étape 2 complète !")