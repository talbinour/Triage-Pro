"""
mongo_service.py — Couche d'accès MongoDB
Toutes les opérations sur les collections passent par ici.
"""
from django.conf import settings
from bson import ObjectId
from datetime import datetime, timedelta


def get_db():
    return settings.MONGO_DB


# ─── Collection Infirmiers ────────────────────────────────────────────────────

def infirmier_collection():
    return get_db()['infirmiers']


def serialize_infirmier(doc, include_password=False):
    """Convertit un document MongoDB en dict JSON-serializable"""
    if not doc:
        return None
    result = {
        'id': str(doc['_id']),
        'email': doc.get('email', ''),
        'nom': doc.get('nom', ''),
        'prenom': doc.get('prenom', ''),
        'nom_complet': f"{doc.get('prenom', '')} {doc.get('nom', '')}",
        'role': doc.get('role', 'infirmier'),
        'statut': doc.get('statut', 'actif'),
        'telephone': doc.get('telephone', ''),
        'service': doc.get('service', ''),
        'date_creation': doc.get('date_creation', '').isoformat()
             if isinstance(doc.get('date_creation'), datetime)
             else str(doc.get('date_creation', '')),
        'date_modification': doc.get('date_modification', '').isoformat()
             if isinstance(doc.get('date_modification'), datetime) 
             else str(doc.get('date_modification', '')),
        'derniere_connexion': doc.get('derniere_connexion', '').isoformat() 
            if isinstance(doc.get('derniere_connexion'), datetime) 
            else None,
        'en_service': doc.get('en_service', False),
        'debut_service': doc.get('debut_service', '').isoformat()
            if isinstance(doc.get('debut_service'), datetime)
            else None,
        'qr_code_base64': doc.get('qr_code_base64', ''),
    }
    if include_password:
        result['password'] = doc.get('password', '')
    return result


def find_infirmier_by_email(email):
    return infirmier_collection().find_one({'email': email})


def find_infirmier_by_id(id_str):
    try:
        return infirmier_collection().find_one({'_id': ObjectId(id_str)})
    except Exception:
        return None


def get_all_infirmiers(role=None, statut=None, search=None):
    query = {}
    if role:
        query['role'] = role
    if statut:
        query['statut'] = statut
    if search:
        query['$or'] = [
            {'nom': {'$regex': search, '$options': 'i'}},
            {'prenom': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'service': {'$regex': search, '$options': 'i'}},
        ]
    return list(infirmier_collection().find(query).sort('date_creation', -1))


def create_infirmier(data):
    data['date_creation'] = datetime.utcnow()
    data['date_modification'] = datetime.utcnow()
    result = infirmier_collection().insert_one(data)
    return infirmier_collection().find_one({'_id': result.inserted_id})


def update_infirmier(id_str, data):
    data['date_modification'] = datetime.utcnow()
    infirmier_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': data}
    )
    return find_infirmier_by_id(id_str)


def delete_infirmier(id_str):
    infirmier_collection().delete_one({'_id': ObjectId(id_str)})


def get_statistiques():
    col = infirmier_collection()
    return {
        'total': col.count_documents({}),
        'actifs': col.count_documents({'statut': 'actif'}),
        'inactifs': col.count_documents({'statut': 'inactif'}),
        'suspendus': col.count_documents({'statut': 'suspendu'}),
        'admins': col.count_documents({'role': 'admin'}),
        'infirmiers': col.count_documents({'role': 'infirmier'}),
    }


def get_infirmiers_en_service():
    """Retourne tous les infirmiers actuellement en service"""
    return list(
        infirmier_collection()
        .find({'en_service': True, 'statut': 'actif'})
        .sort('debut_service', -1)
    )


def toggle_service(id_str: str, en_service: bool):
    """
    Met un infirmier en service ou hors service.
    Quand on le met en service → enregistre l'heure de début.
    Quand on le retire → efface l'heure.
    """
    update_data = {
        'en_service': en_service,
        'date_modification': datetime.utcnow(),
    }
    if en_service:
        update_data['debut_service'] = datetime.utcnow()
    else:
        update_data['debut_service'] = None

    infirmier_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': update_data}
    )
    return find_infirmier_by_id(id_str)


def compter_infirmiers_en_service():
    """Retourne le nombre d'infirmiers en service"""
    return infirmier_collection().count_documents({
        'en_service': True,
        'statut': 'actif'
    })

# ─── Remarques / Réclamations ─────────────────────────────────────────────────

def remarque_collection():
    return get_db()['remarques']


def create_remarque(data):
    data['date_creation'] = datetime.utcnow()
    data['lue'] = False
    result = remarque_collection().insert_one(data)
    return remarque_collection().find_one({'_id': result.inserted_id})


def get_remarques_by_infirmier(infirmier_id):
    return list(
        remarque_collection()
        .find({'infirmier_id': infirmier_id})
        .sort('date_creation', -1)
    )


def get_toutes_remarques():
    return list(
        remarque_collection()
        .find()
        .sort('date_creation', -1)
    )


def serialize_remarque(doc):
    if not doc:
        return None
    return {
        'id': str(doc['_id']),
        'infirmier_id': doc.get('infirmier_id', ''),
        'infirmier_nom': doc.get('infirmier_nom', ''),
        'type': doc.get('type', 'remarque'),
        'sujet': doc.get('sujet', ''),
        'message': doc.get('message', ''),
        'lue': doc.get('lue', False),
        'reponse': doc.get('reponse', ''),
        'date_creation': doc.get('date_creation', '').isoformat()
            if isinstance(doc.get('date_creation'), datetime)
            else str(doc.get('date_creation', '')),
    }


def marquer_remarque_lue(id_str):
    remarque_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': {'lue': True}}
    )


def repondre_remarque(id_str, reponse):
    remarque_collection().update_one(
        {'_id': ObjectId(id_str)},
        {'$set': {'reponse': reponse, 'lue': True}}
    )

# ─── Planning des services ────────────────────────────────────────────────────

def planning_collection():
    return get_db()['planning']


def get_planning_semaine(date_debut_str=None):
    """
    Retourne le planning de la semaine.
    date_debut_str format : 'YYYY-MM-DD' (lundi de la semaine)
    Si None, retourne la semaine en cours.
    """
    if date_debut_str:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
    else:
        today = datetime.now()
        date_debut = today - timedelta(days=today.weekday())

    date_debut = date_debut.replace(hour=0, minute=0, second=0, microsecond=0)
    date_fin = date_debut + timedelta(days=7)

    plannings = list(
        planning_collection()
        .find({
            'date': {'$gte': date_debut, '$lt': date_fin}
        })
        .sort('date', 1)
    )
    return plannings


def serialize_planning(doc):
    if not doc:
        return None
    return {
        'id': str(doc['_id']),
        'infirmier_id': doc.get('infirmier_id', ''),
        'infirmier_nom': doc.get('infirmier_nom', ''),
        'date': doc.get('date').strftime('%Y-%m-%d') if isinstance(doc.get('date'), datetime) else str(doc.get('date', '')),
        'creneau': doc.get('creneau', ''),
    }


def ajouter_planning(infirmier_id, infirmier_nom, date_str, creneau):
    """
    Ajoute un infirmier à un créneau.
    creneau : 'matin' ou 'soir'
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')

    # Vérifier doublon
    existe = planning_collection().find_one({
        'infirmier_id': infirmier_id,
        'date': date_obj,
        'creneau': creneau
    })
    if existe:
        return existe

    doc = {
        'infirmier_id': infirmier_id,
        'infirmier_nom': infirmier_nom,
        'date': date_obj,
        'creneau': creneau,
    }
    result = planning_collection().insert_one(doc)
    return planning_collection().find_one({'_id': result.inserted_id})


def supprimer_planning(infirmier_id, date_str, creneau):
    """Retire un infirmier d'un créneau"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    planning_collection().delete_one({
        'infirmier_id': infirmier_id,
        'date': date_obj,
        'creneau': creneau
    })


def get_planning_jour(date_str):
    """Retourne les infirmiers en service pour un jour donné"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_fin = date_obj + timedelta(days=1)
    return list(
        planning_collection()
        .find({'date': {'$gte': date_obj, '$lt': date_fin}})
    )