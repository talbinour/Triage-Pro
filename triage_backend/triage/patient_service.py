# triage/patient_service.py

from django.conf import settings
from bson import ObjectId
from datetime import datetime


def patient_collection():
    return settings.MONGO_DB['patients']

def _get_delai_max(niveau):
    """Retourne le délai max en minutes pour un niveau donné"""
    delais = {1: 2, 2: 10, 3: 30, 4: 60, 5: 120}
    return delais.get(niveau, None)

def serialize_patient(doc):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if not doc:
        return None
    return {
        'id':          str(doc['_id']),
        'nom':         doc.get('nom', ''),
        'prenom':      doc.get('prenom', ''),
        'age':         doc.get('age'),
        'sexe':        doc.get('sexe', ''),
        'temperature': doc.get('temperature'),
        'oxygene':     doc.get('oxygene'),
        'pouls':       doc.get('pouls'),
        'symptome1':   doc.get('symptome1', ''),
        'symptome2':   doc.get('symptome2', ''),
        'degre_urgence':  doc.get('degre_urgence', None),
        'statut':         doc.get('statut', 'en_attente'),
        'infirmier_id':   doc.get('infirmier_id', ''),
        'infirmier_nom':  doc.get('infirmier_nom', ''),
        'lit_id':          doc.get('lit_id', ''),
        'lit_numero':      doc.get('lit_numero', ''),
        'delai_max_minutes': _get_delai_max(doc.get('degre_urgence')),
        'date_creation': doc.get('date_creation', '').isoformat()
            if isinstance(doc.get('date_creation'), datetime)
            else str(doc.get('date_creation', '')),
    }


def creer_patient(data: dict):
    """Insère un nouveau patient et retourne le document créé"""
    data['date_creation'] = datetime.now()
    data['statut'] = 'en_attente'
    result = patient_collection().insert_one(data)
    return patient_collection().find_one({'_id': result.inserted_id})


def get_tous_patients():
    """Retourne tous les patients triés : urgence d'abord, puis date"""
    return list(
        patient_collection()
        .find()
        .sort([('degre_urgence', 1), ('date_creation', 1)])
    )


def get_patient_by_id(id_str: str):
    try:
        return patient_collection().find_one({'_id': ObjectId(id_str)})
    except Exception:
        return None
    
def supprimer_patient(id_str: str):
    try:
        patient_collection().delete_one({'_id': ObjectId(id_str)})
    except Exception:
        pass


def update_patient(id_str: str, data: dict):
    """Met à jour un patient par id et retourne le document mis à jour"""
    try:
        # Ne pas écraser _id
        if '_id' in data:
            data.pop('_id')
        patient_collection().update_one(
            {'_id': ObjectId(id_str)},
            {'$set': data}
        )
        return patient_collection().find_one({'_id': ObjectId(id_str)})
    except Exception:
        return None
    

def prendre_en_charge(patient_id: str, lit_id: str, lit_numero: str):
    """
    Passe le patient de 'en_attente' à 'en_consultation'
    et enregistre le lit assigné.
    """
    patient_collection().update_one(
        {'_id': ObjectId(patient_id)},
        {'$set': {
            'statut': 'en_consultation',
            'lit_id': lit_id,
            'lit_numero': lit_numero,
            'date_prise_en_charge': datetime.now(),
        }}
    )
    return patient_collection().find_one(
        {'_id': ObjectId(patient_id)}
    )


def terminer_patient(patient_id: str):
    """
    Passe le patient à 'termine'.
    Ne supprime pas — archive pour les statistiques.
    """
    patient_collection().update_one(
        {'_id': ObjectId(patient_id)},
        {'$set': {
            'statut': 'termine',
            'date_fin': datetime.now(),
        }}
    )
    return patient_collection().find_one(
        {'_id': ObjectId(patient_id)}
    )


def get_patients_en_attente():
    """Retourne les patients en attente, triés par urgence"""
    return list(
        patient_collection()
        .find({'statut': 'en_attente'})
        .sort([('degre_urgence', 1), ('date_creation', 1)])
    )


def get_patients_en_consultation():
    """Retourne les patients en consultation"""
    return list(
        patient_collection()
        .find({'statut': 'en_consultation'})
        .sort('date_prise_en_charge', 1)
    )


def compter_patients_par_niveau():
    """
    Compte les patients en attente par niveau d'urgence.
    Utilisé par le moteur d'alertes.
    """
    pipeline = [
        {'$match': {'statut': 'en_attente'}},
        {'$group': {
            '_id': '$degre_urgence',
            'count': {'$sum': 1}
        }}
    ]
    resultats = patient_collection().aggregate(pipeline)
    compteurs = {}
    for r in resultats:
        niveau = r['_id']
        if niveau is not None:
            compteurs[f'P{niveau}'] = r['count']
    return compteurs
def get_patients_termines(limite=50):
    """Retourne les patients terminés (archivés), les plus récents d'abord"""
    return list(
        patient_collection()
        .find({'statut': 'termine'})
        .sort('date_fin', -1)
        .limit(limite)
    )


def get_statistiques_avancees():
    """
    Retourne les statistiques avancées pour le dashboard admin :
    - temps d'attente moyen par niveau
    - taux de correction manuelle
    - affluence par heure (24h)
    - totaux
    """
    from datetime import timedelta

    maintenant = datetime.now()
    il_y_a_24h = maintenant - timedelta(hours=24)
    il_y_a_7j = maintenant - timedelta(days=7)
    aujourdhui = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Temps d'attente moyen par niveau ──────
    temps_attente_par_niveau = {}
    for niveau in range(1, 6):
        pipeline = [
            {'$match': {
                'statut': 'termine',
                'degre_urgence': niveau,
                'date_creation': {'$exists': True},
                'date_prise_en_charge': {'$exists': True},
            }},
            {'$project': {
                'attente': {
                    '$subtract': ['$date_prise_en_charge', '$date_creation']
                }
            }},
            {'$group': {
                '_id': None,
                'moyenne_ms': {'$avg': '$attente'},
                'count': {'$sum': 1}
            }}
        ]
        result = list(patient_collection().aggregate(pipeline))
        if result and result[0].get('moyenne_ms'):
            moyenne_min = round(result[0]['moyenne_ms'] / 60000, 1)
            temps_attente_par_niveau[f'P{niveau}'] = {
                'moyenne_minutes': moyenne_min,
                'count': result[0]['count']
            }

    # ── Taux de correction manuelle ───────────
    total_avec_urgence = patient_collection().count_documents({
        'degre_urgence': {'$ne': None}
    })
    total_corriges = patient_collection().count_documents({
        'correction_manuelle': True
    })
    taux_correction = round(
        (total_corriges / total_avec_urgence * 100), 1
    ) if total_avec_urgence > 0 else 0

    # ── Affluence par heure (24h) ─────────────
    affluence = []
    for h in range(24):
        heure_debut = il_y_a_24h + timedelta(hours=h)
        heure_fin = heure_debut + timedelta(hours=1)
        count = patient_collection().count_documents({
            'date_creation': {
                '$gte': heure_debut,
                '$lt': heure_fin
            }
        })
        affluence.append({
            'heure': heure_debut.strftime('%Hh'),
            'count': count
        })

    # ── Totaux ────────────────────────────────
    total_patients = patient_collection().count_documents({})
    termines_aujourdhui = patient_collection().count_documents({
        'statut': 'termine',
        'date_fin': {'$gte': aujourdhui}
    })
    termines_semaine = patient_collection().count_documents({
        'statut': 'termine',
        'date_fin': {'$gte': il_y_a_7j}
    })

    return {
        'temps_attente_par_niveau': temps_attente_par_niveau,
        'taux_correction': taux_correction,
        'total_corriges': total_corriges,
        'total_avec_urgence': total_avec_urgence,
        'affluence_24h': affluence,
        'totaux': {
            'total_patients': total_patients,
            'termines_aujourdhui': termines_aujourdhui,
            'termines_semaine': termines_semaine,
        }
    }