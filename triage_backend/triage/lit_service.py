
from django.conf import settings
from bson import ObjectId
from datetime import datetime


def lit_collection():
    """Retourne la collection MongoDB 'lits'"""
    return settings.MONGO_DB['lits']


def serialize_lit(doc):
    """Convertit un document MongoDB en dict JSON"""
    if not doc:
        return None
    return {
        'id':               str(doc['_id']),
        'numero':           doc.get('numero', ''),
        'type':             doc.get('type', ''),
        'categorie':        doc.get('categorie', ''),
        'statut':           doc.get('statut', 'libre'),
        'patient_id':       doc.get('patient_id', ''),
        'patient_nom':      doc.get('patient_nom', ''),
        'date_occupation':  doc.get('date_occupation', '').isoformat()
            if isinstance(doc.get('date_occupation'), datetime)
            else None,
    }


def get_tous_lits(type_filtre=None, statut_filtre=None):
    """Retourne tous les lits avec filtres optionnels"""
    query = {}
    if type_filtre:
        query['type'] = type_filtre
    if statut_filtre:
        query['statut'] = statut_filtre
    return list(
        lit_collection()
        .find(query)
        .sort([('type', 1), ('numero', 1)])
    )


def get_lit_by_id(id_str):
    """Retourne un lit par son ID"""
    try:
        return lit_collection().find_one({'_id': ObjectId(id_str)})
    except Exception:
        return None


def get_lits_libres(type_filtre=None):
    """Retourne les lits libres, avec filtre optionnel par type"""
    query = {'statut': 'libre'}
    if type_filtre:
        query['type'] = type_filtre
    return list(
        lit_collection()
        .find(query)
        .sort([('type', 1), ('numero', 1)])
    )


def occuper_lit(lit_id: str, patient_id: str, patient_nom: str):
    """
    Marque un lit comme occupé par un patient.
    Appelé quand l'infirmier prend en charge un patient.
    """
    lit_collection().update_one(
        {'_id': ObjectId(lit_id)},
        {'$set': {
            'statut': 'occupe',
            'patient_id': patient_id,
            'patient_nom': patient_nom,
            'date_occupation': datetime.utcnow(),
        }}
    )
    return get_lit_by_id(lit_id)


def liberer_lit(lit_id: str):
    """
    Libère un lit — remet à 'libre' et efface le patient.
    Appelé quand la consultation est terminée.
    """
    lit_collection().update_one(
        {'_id': ObjectId(lit_id)},
        {'$set': {
            'statut': 'libre',
            'patient_id': '',
            'patient_nom': '',
            'date_occupation': None,
        }}
    )
    return get_lit_by_id(lit_id)


def liberer_lit_par_patient(patient_id: str):
    """
    Libère le lit occupé par un patient donné.
    Utile quand on termine le patient sans connaître le lit.
    """
    lit = lit_collection().find_one({
        'patient_id': patient_id,
        'statut': 'occupe'
    })
    if lit:
        return liberer_lit(str(lit['_id']))
    return None


def creer_lit(data: dict):
    """Crée un nouveau lit/cabine"""
    document = {
        'numero':      data.get('numero', ''),
        'type':        data.get('type', ''),
        'categorie':   data.get('categorie', ''),
        'statut':      'libre',
        'patient_id':  '',
        'patient_nom': '',
        'date_occupation': None,
    }
    result = lit_collection().insert_one(document)
    return lit_collection().find_one({'_id': result.inserted_id})


def supprimer_lit(id_str: str):
    """Supprime un lit par son ID"""
    lit_collection().delete_one({'_id': ObjectId(id_str)})


def get_resume_lits():
    """
    Résumé pour le dashboard : combien de lits
    libres/occupés par type.
    """
    tous = get_tous_lits()
    resume = {}

    for lit in tous:
        type_lit = lit.get('type', 'autre')
        if type_lit not in resume:
            resume[type_lit] = {
                'type': type_lit,
                'categorie': lit.get('categorie', ''),
                'total': 0,
                'libres': 0,
                'occupes': 0,
            }
        resume[type_lit]['total'] += 1
        if lit.get('statut') == 'libre':
            resume[type_lit]['libres'] += 1
        else:
            resume[type_lit]['occupes'] += 1

    return list(resume.values())


def initialiser_lits_defaut():
    """
    Crée les lits par défaut si la collection est vide.
    Appelé une seule fois au premier lancement.
    """
    if lit_collection().count_documents({}) > 0:
        return  # Déjà initialisé

    lits_defaut = [
        # Réanimation (P1) — 5 lits
        {'numero': 'R-01', 'type': 'reanimation', 'categorie': 'P1'},
        {'numero': 'R-02', 'type': 'reanimation', 'categorie': 'P1'},
        {'numero': 'R-03', 'type': 'reanimation', 'categorie': 'P1'},
        {'numero': 'R-04', 'type': 'reanimation', 'categorie': 'P1'},
        {'numero': 'R-05', 'type': 'reanimation', 'categorie': 'P1'},

        # Urgence (P2-P3) — 10 lits
        {'numero': 'U-01', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-02', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-03', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-04', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-05', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-06', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-07', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-08', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-09', 'type': 'urgence', 'categorie': 'P2-P3'},
        {'numero': 'U-10', 'type': 'urgence', 'categorie': 'P2-P3'},

        # Observation (P4-P5) — 15 lits
        {'numero': 'O-01', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-02', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-03', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-04', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-05', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-06', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-07', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-08', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-09', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-10', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-11', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-12', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-13', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-14', 'type': 'observation', 'categorie': 'P4-P5'},
        {'numero': 'O-15', 'type': 'observation', 'categorie': 'P4-P5'},
    ]

    for lit in lits_defaut:
        creer_lit(lit)

    print("✓ 30 lits par défaut initialisés "
          "(5 réa + 10 urgence + 15 observation)")