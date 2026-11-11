

from django.conf import settings
from bson import ObjectId
from datetime import datetime, timedelta

from .patient_service import (
    compter_patients_par_niveau,
    get_patients_en_attente,
    patient_collection,
)
from .lit_service import get_resume_lits, get_tous_lits
from .equipement_service import get_tous_equipements
from .mongo_service import compter_infirmiers_en_service

# ── Délais maximum par niveau (en minutes) ────
DELAI_MAX = {
    1: 2,     # P1 — immédiat
    2: 10,    # P2 — 10 minutes
    3: 30,    # P3 — 30 minutes
    4: 60,    # P4 — 1 heure
    5: 120,   # P5 — 2 heures
}


# ─── Collection alertes (historique) ──────────────────────

def alerte_collection():
    """Retourne la collection MongoDB 'alertes'"""
    return settings.MONGO_DB['alertes']


def serialize_alerte(doc):
    """Convertit un document MongoDB en dict JSON"""
    if not doc:
        return None
    return {
        'id':        str(doc['_id']),
        'type':      doc.get('type', ''),
        'severite':  doc.get('severite', 'info'),
        'message':   doc.get('message', ''),
        'details':   doc.get('details', ''),
        'lue':       doc.get('lue', False),
        'date':      doc.get('date', '').isoformat()
            if isinstance(doc.get('date'), datetime)
            else str(doc.get('date', '')),
    }


def sauvegarder_alerte(alerte: dict):
    """Enregistre une alerte dans l'historique MongoDB"""
    alerte['date'] = datetime.utcnow()
    alerte['lue'] = False
    result = alerte_collection().insert_one(alerte)
    return alerte_collection().find_one(
        {'_id': result.inserted_id}
    )


def get_alertes_recentes(limite=50):
    """Retourne les alertes les plus récentes"""
    return list(
        alerte_collection()
        .find()
        .sort('date', -1)
        .limit(limite)
    )


def get_alertes_non_lues():
    """Retourne le nombre d'alertes non lues"""
    return alerte_collection().count_documents({'lue': False})


def marquer_alerte_lue(id_str: str):
    """Marque une alerte comme lue"""
    alerte_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': {'lue': True}}
    )


def marquer_toutes_lues():
    """Marque toutes les alertes comme lues"""
    alerte_collection().update_many(
        {'lue': False},
        {'$set': {'lue': True}}
    )


# ─── Moteur d'analyse ────────────────────────────────────

def analyser_situation():
    """
    Analyse complète de la situation aux urgences.
    Croise patients en attente × ressources disponibles.
    Retourne une liste d'alertes générées.

    C'est cette fonction qui est appelée par le dashboard
    pour afficher les alertes en temps réel.
    """
    alertes = []

    # ── Données d'entrée ──────────────────────
    patients_par_niveau = compter_patients_par_niveau()
    resume_lits = get_resume_lits()
    equipements = get_tous_equipements()
    nb_infirmiers = compter_infirmiers_en_service()

    total_patients_attente = sum(patients_par_niveau.values())

    # ── 1. ALERTES PERSONNEL ──────────────────
    alertes += _analyser_personnel(
        nb_infirmiers, total_patients_attente,
        patients_par_niveau
    )

    # ── 2. ALERTES LITS ──────────────────────
    alertes += _analyser_lits(
        resume_lits, patients_par_niveau
    )

    # ── 3. ALERTES ÉQUIPEMENTS ───────────────
    alertes += _analyser_equipements(equipements)

    # ── 4. ALERTES FLUX ──────────────────────
    alertes += _analyser_flux()

    # ── 5. ALERTES DÉPASSEMENTS ──────────────
    alertes += _analyser_depassements()
    return alertes


def _analyser_personnel(nb_infirmiers, total_patients, par_niveau):
    """Analyse le ratio patients / infirmiers en service"""
    alertes = []

    if nb_infirmiers == 0:
        alertes.append({
            'type': 'personnel',
            'severite': 'critique',
            'message': 'Aucun infirmier en service',
            'details': f'{total_patients} patient(s) en attente '
                       f'sans personnel disponible.',
        })
        return alertes

    # Ratio patients critiques (P1+P2) par infirmier
    critiques = par_niveau.get('P1', 0) + par_niveau.get('P2', 0)
    ratio = total_patients / nb_infirmiers

    if critiques > 0 and critiques > nb_infirmiers:
        alertes.append({
            'type': 'personnel',
            'severite': 'critique',
            'message': 'Surcharge personnel — patients critiques',
            'details': f'{critiques} patient(s) P1/P2 en attente '
                       f'pour {nb_infirmiers} infirmier(s) en service. '
                       f'Ratio : {ratio:.1f} patients/infirmier.',
        })
    elif ratio > 5:
        alertes.append({
            'type': 'personnel',
            'severite': 'avertissement',
            'message': 'Charge élevée par infirmier',
            'details': f'{total_patients} patients pour '
                       f'{nb_infirmiers} infirmier(s). '
                       f'Ratio : {ratio:.1f} patients/infirmier.',
        })
    elif ratio > 3:
        alertes.append({
            'type': 'personnel',
            'severite': 'info',
            'message': 'Charge modérée',
            'details': f'Ratio : {ratio:.1f} patients/infirmier. '
                       f'Situation sous contrôle.',
        })

    return alertes


def _analyser_lits(resume_lits, par_niveau):
    """Analyse la disponibilité des lits par rapport aux patients"""
    alertes = []

    # Mapping catégorie lit → niveaux patients concernés
    mapping = {
        'reanimation': ['P1'],
        'urgence':     ['P2', 'P3'],
        'observation': ['P4', 'P5'],
    }

    for resume in resume_lits:
        type_lit = resume['type']
        libres = resume['libres']
        total = resume['total']

        # Patients concernés par ce type de lit
        niveaux = mapping.get(type_lit, [])
        patients_concernes = sum(
            par_niveau.get(n, 0) for n in niveaux
        )

        if libres == 0 and patients_concernes > 0:
            alertes.append({
                'type': 'lits',
                'severite': 'critique',
                'message': f'Aucun lit {type_lit} disponible',
                'details': f'{patients_concernes} patient(s) '
                           f'{"/".join(niveaux)} en attente '
                           f'mais 0/{total} lit(s) {type_lit} '
                           f'disponible(s).',
            })
        elif libres <= 2 and patients_concernes > libres:
            alertes.append({
                'type': 'lits',
                'severite': 'avertissement',
                'message': f'Lits {type_lit} presque saturés',
                'details': f'{libres}/{total} lit(s) libre(s) '
                           f'pour {patients_concernes} patient(s) '
                           f'{"/".join(niveaux)} en attente.',
            })

    return alertes


def _analyser_equipements(equipements):
    """Vérifie les seuils d'alerte des équipements"""
    alertes = []

    for eq in equipements:
        disponible = eq.get('disponible', 0)
        seuil = eq.get('seuil_alerte', 0)
        nom = eq.get('nom', '')
        total = eq.get('total', 0)

        if disponible == 0:
            alertes.append({
                'type': 'equipement',
                'severite': 'critique',
                'message': f'{nom} — aucun disponible',
                'details': f'0/{total} {nom.lower()} disponible(s). '
                           f'Réapprovisionnement nécessaire.',
            })
        elif disponible <= seuil:
            alertes.append({
                'type': 'equipement',
                'severite': 'avertissement',
                'message': f'{nom} — seuil d\'alerte atteint',
                'details': f'{disponible}/{total} disponible(s). '
                           f'Seuil d\'alerte : {seuil}.',
            })

    return alertes


def _analyser_flux():
    """
    Analyse la tendance d'arrivée des patients.
    Compare la dernière heure à la moyenne habituelle.
    """
    alertes = []

    maintenant = datetime.utcnow()
    il_y_a_1h = maintenant - timedelta(hours=1)
    il_y_a_24h = maintenant - timedelta(hours=24)

    # Patients arrivés dans la dernière heure
    arrivees_1h = patient_collection().count_documents({
        'date_creation': {'$gte': il_y_a_1h}
    })

    # Moyenne horaire sur les 24 dernières heures
    arrivees_24h = patient_collection().count_documents({
        'date_creation': {'$gte': il_y_a_24h}
    })
    moyenne_horaire = arrivees_24h / 24 if arrivees_24h > 0 else 0

    # Affluence inhabituelle : si > 1.5× la moyenne
    if moyenne_horaire > 0 and arrivees_1h > moyenne_horaire * 1.5:
        alertes.append({
            'type': 'flux',
            'severite': 'avertissement',
            'message': 'Affluence inhabituelle détectée',
            'details': f'{arrivees_1h} arrivée(s) dans la '
                       f'dernière heure contre une moyenne de '
                       f'{moyenne_horaire:.1f}/heure. '
                       f'Préparez des ressources supplémentaires.',
        })

    return alertes

def _analyser_depassements():
    """
    Vérifie si des patients en attente ont dépassé
    le délai maximum recommandé pour leur niveau.
    """
    alertes = []
    maintenant = datetime.utcnow()
    patients = get_patients_en_attente()

    depassements_critiques = []
    depassements_warning = []

    for p in patients:
        niveau = p.get('degre_urgence')
        if niveau is None:
            continue

        date_creation = p.get('date_creation')
        if not isinstance(date_creation, datetime):
            continue

        delai_max = DELAI_MAX.get(niveau, 120)
        attente_min = (maintenant - date_creation).total_seconds() / 60

        if attente_min > delai_max:
            nom = f"{p.get('prenom', '')} {p.get('nom', '')}"
            depassement = round(attente_min - delai_max)

            if niveau <= 2:
                depassements_critiques.append({
                    'nom': nom,
                    'niveau': f'P{niveau}',
                    'attente': round(attente_min),
                    'depassement': depassement,
                })
            else:
                depassements_warning.append({
                    'nom': nom,
                    'niveau': f'P{niveau}',
                    'attente': round(attente_min),
                    'depassement': depassement,
                })

    if depassements_critiques:
        details = '; '.join([
            f"{d['nom']} ({d['niveau']}, +{d['depassement']}min)"
            for d in depassements_critiques
        ])
        alertes.append({
            'type': 'depassement',
            'severite': 'critique',
            'message': f"{len(depassements_critiques)} patient(s) "
                       f"critique(s) en attente trop longtemps",
            'details': details,
        })

    if depassements_warning:
        details = '; '.join([
            f"{d['nom']} ({d['niveau']}, +{d['depassement']}min)"
            for d in depassements_warning
        ])
        alertes.append({
            'type': 'depassement',
            'severite': 'avertissement',
            'message': f"{len(depassements_warning)} patient(s) "
                       f"dépassent le délai recommandé",
            'details': details,
        })

    return alertes
# ─── Dashboard — données complètes ───────────────────────

def get_dashboard_data():
    """
    Retourne toutes les données nécessaires au dashboard
    admin en un seul appel. C'est l'API principale du
    Sprint 5.
    """
    patients_par_niveau = compter_patients_par_niveau()
    resume_lits = get_resume_lits()
    equipements = get_tous_equipements()
    from .equipement_service import serialize_equipement

    # Générer les alertes en temps réel
    alertes_live = analyser_situation()

    # Sauvegarder les alertes critiques dans l'historique
    for alerte in alertes_live:
        if alerte['severite'] == 'critique':
            # Éviter les doublons : ne pas re-sauvegarder
            # la même alerte critique dans les 10 dernières min
            deja = alerte_collection().find_one({
                'message': alerte['message'],
                'date': {'$gte': datetime.utcnow() - timedelta(minutes=10)}
            })
            if not deja:
                sauvegarder_alerte(alerte)

    return {
        # Compteurs patients
        'patients': {
            'par_niveau': patients_par_niveau,
            'total_attente': sum(patients_par_niveau.values()),
            'en_consultation': patient_collection().count_documents(
                {'statut': 'en_consultation'}
            ),
            'termines_aujourdhui': patient_collection().count_documents({
                'statut': 'termine',
                'date_fin': {
                    '$gte': datetime.utcnow().replace(
                        hour=0, minute=0, second=0
                    )
                }
            }),
        },

        # Ressources
        'lits': resume_lits,
        'equipements': [
            serialize_equipement(eq) for eq in equipements
        ],
        'personnel': {
            'en_service': compter_infirmiers_en_service(),
        },

        # Alertes
        'alertes': alertes_live,
        'alertes_non_lues': get_alertes_non_lues(),
    }