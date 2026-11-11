
from django.conf import settings
from bson import ObjectId
from datetime import datetime


def equipement_collection():
    """Retourne la collection MongoDB 'equipements'"""
    return settings.MONGO_DB['equipements']


def serialize_equipement(doc):
    """Convertit un document MongoDB en dict JSON"""
    if not doc:
        return None
    return {
        'id':              str(doc['_id']),
        'nom':             doc.get('nom', ''),
        'total':           doc.get('total', 0),
        'disponible':      doc.get('disponible', 0),
        'seuil_alerte':    doc.get('seuil_alerte', 0),
        'unite':           doc.get('unite', ''),
        'date_modification': doc.get('date_modification', '').isoformat()
            if isinstance(doc.get('date_modification'), datetime)
            else str(doc.get('date_modification', '')),
    }


def get_tous_equipements():
    """Retourne tous les équipements"""
    return list(
        equipement_collection()
        .find()
        .sort('nom', 1)
    )


def get_equipement_by_id(id_str):
    """Retourne un équipement par son ID"""
    try:
        return equipement_collection().find_one(
            {'_id': ObjectId(id_str)}
        )
    except Exception:
        return None


def creer_equipement(data: dict):
    """Crée un nouvel équipement"""
    document = {
        'nom':             data.get('nom', ''),
        'total':           int(data.get('total', 0)),
        'disponible':      int(data.get('disponible', 0)),
        'seuil_alerte':    int(data.get('seuil_alerte', 0)),
        'unite':           data.get('unite', 'appareils'),
        'date_modification': datetime.utcnow(),
    }
    result = equipement_collection().insert_one(document)
    return equipement_collection().find_one(
        {'_id': result.inserted_id}
    )


def update_equipement(id_str: str, data: dict):
    """Met à jour un équipement"""
    for champ in ['total', 'disponible', 'seuil_alerte']:
        if champ in data:
            data[champ] = int(data[champ])
    data['date_modification'] = datetime.utcnow()

    equipement_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': data}
    )
    return get_equipement_by_id(id_str)


def supprimer_equipement(id_str: str):
    """Supprime un équipement"""
    equipement_collection().delete_one(
        {'_id': ObjectId(id_str)}
    )


def utiliser_equipement(id_str: str):
    """
    Décrémente le disponible de 1.
    Appelé quand un équipement est assigné à un patient.
    """
    eq = get_equipement_by_id(id_str)
    if not eq or eq.get('disponible', 0) <= 0:
        return None

    equipement_collection().update_one(
        {'_id': ObjectId(id_str)},
        {
            '$inc': {'disponible': -1},
            '$set': {'date_modification': datetime.utcnow()}
        }
    )
    return get_equipement_by_id(id_str)


def liberer_equipement(id_str: str):
    """
    Incrémente le disponible de 1.
    Appelé quand un équipement est libéré.
    """
    eq = get_equipement_by_id(id_str)
    if not eq:
        return None

    # Ne pas dépasser le total
    if eq.get('disponible', 0) >= eq.get('total', 0):
        return eq

    equipement_collection().update_one(
        {'_id': ObjectId(id_str)},
        {
            '$inc': {'disponible': 1},
            '$set': {'date_modification': datetime.utcnow()}
        }
    )
    return get_equipement_by_id(id_str)


def initialiser_equipements_defaut():
    """
    Crée les équipements par défaut si la collection est vide.
    """
    if equipement_collection().count_documents({}) > 0:
        return

    equipements_defaut = [
        {
            'nom': 'Respirateurs',
            'total': 6,
            'disponible': 6,
            'seuil_alerte': 2,
            'unite': 'appareils',
        },
        {
            'nom': 'Défibrillateurs',
            'total': 4,
            'disponible': 4,
            'seuil_alerte': 1,
            'unite': 'appareils',
        },
        {
            'nom': 'Moniteurs cardiaques',
            'total': 8,
            'disponible': 8,
            'seuil_alerte': 2,
            'unite': 'appareils',
        },
        {
            'nom': 'Pompes à perfusion',
            'total': 12,
            'disponible': 12,
            'seuil_alerte': 3,
            'unite': 'appareils',
        },
    ]

    for eq in equipements_defaut:
        creer_equipement(eq)

    print("✓ 4 équipements par défaut initialisés")