import json
import threading
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .ai.predict_service import predire_niveau_urgence

from .mongo_service import (
    find_infirmier_by_email, find_infirmier_by_id,
    get_all_infirmiers, create_infirmier, update_infirmier,
    delete_infirmier, get_statistiques, serialize_infirmier,
    infirmier_collection
)
from .auth_utils import hash_password, check_password, generate_token, decode_token
from .email_service import envoyer_email_bienvenue, generer_qr_code
from .qr_auth_service import generer_qr_token, sauvegarder_qr_token, valider_qr_token
from .patient_service import (
    creer_patient, get_tous_patients,
    get_patient_by_id, serialize_patient, update_patient
)
from .lit_service import (
    get_tous_lits, get_lits_libres, get_lit_by_id,
    creer_lit, supprimer_lit, occuper_lit, liberer_lit,
    liberer_lit_par_patient, get_resume_lits,
    serialize_lit, initialiser_lits_defaut
)
from .equipement_service import (
    get_tous_equipements, get_equipement_by_id,
    creer_equipement, update_equipement, supprimer_equipement,
    utiliser_equipement, liberer_equipement,
    serialize_equipement, initialiser_equipements_defaut
)
from .alerte_service import (
    get_dashboard_data, analyser_situation,
    get_alertes_recentes, marquer_alerte_lue,
    marquer_toutes_lues, get_alertes_non_lues,
    serialize_alerte
)
from .patient_service import (
    prendre_en_charge, terminer_patient,
    get_patients_en_attente, get_patients_en_consultation
)
from .mongo_service import (
    create_remarque, get_remarques_by_infirmier,
    get_toutes_remarques, serialize_remarque,
    marquer_remarque_lue, repondre_remarque
)
from .mongo_service import toggle_service, get_infirmiers_en_service
from .mongo_service import (
    get_planning_semaine, serialize_planning,
    ajouter_planning, supprimer_planning
)
from .patient_service import get_patients_termines, get_statistiques_avancees
from .mongo_service import get_planning_semaine
from .patient_service import patient_collection
# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_current_user(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    payload = decode_token(auth.split(' ', 1)[1])
    if not payload:
        return None
    return find_infirmier_by_id(payload['user_id'])


def require_auth(func):
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return JsonResponse({'error': 'Non authentifié.'}, status=401)
        request.current_user = user
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def require_admin(func):
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return JsonResponse({'error': 'Non authentifié.'}, status=401)
        if user.get('role') != 'admin':
            return JsonResponse({'error': 'Accès réservé aux administrateurs.'}, status=403)
        request.current_user = user
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def body(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    data = body(request)
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse({'error': 'Email et mot de passe requis.'}, status=400)

    user = find_infirmier_by_email(email)
    if not user or not check_password(password, user.get('password', '')):
        return JsonResponse({'error': 'Email ou mot de passe incorrect.'}, status=400)
    if user.get('statut') != 'actif':
        return JsonResponse({'error': 'Ce compte est désactivé.'}, status=403)

    infirmier_collection().update_one(
        {'_id': user['_id']},
        {'$set': {'derniere_connexion': datetime.utcnow()}}
    )
    token = generate_token(str(user['_id']), user.get('role', 'infirmier'))
    return JsonResponse({'token': token, 'user': serialize_infirmier(user)})


@csrf_exempt
@require_http_methods(['POST'])
def qr_login(request):
    """Connexion par scan de QR code"""
    data = body(request)
    qr_token = data.get('qr_token', '').strip()

    if not qr_token:
        return JsonResponse({'error': 'Token QR manquant.'}, status=400)

    user = valider_qr_token(qr_token)
    if not user:
        return JsonResponse({'error': 'QR code invalide ou compte désactivé.'}, status=401)

    infirmier_collection().update_one(
        {'_id': user['_id']},
        {'$set': {'derniere_connexion': datetime.utcnow()}}
    )
    token = generate_token(str(user['_id']), user.get('role', 'infirmier'))
    return JsonResponse({'token': token, 'user': serialize_infirmier(user)})


@csrf_exempt
@require_http_methods(['GET'])
@require_auth
def me(request):
    return JsonResponse(serialize_infirmier(request.current_user))


@csrf_exempt
@require_http_methods(['POST'])
@require_auth
def changer_mot_de_passe(request):
    data = body(request)
    user = request.current_user
    ancien = data.get('ancien_mot_de_passe', '')
    nouveau = data.get('nouveau_mot_de_passe', '')
    confirmation = data.get('confirmation', '')

    if not check_password(ancien, user.get('password', '')):
        return JsonResponse({'error': 'Mot de passe actuel incorrect.'}, status=400)
    if len(nouveau) < 8:
        return JsonResponse({'error': 'Minimum 8 caractères.'}, status=400)
    if nouveau != confirmation:
        return JsonResponse({'error': 'Les mots de passe ne correspondent pas.'}, status=400)

    infirmier_collection().update_one(
        {'_id': user['_id']},
        {'$set': {'password': hash_password(nouveau), 'date_modification': datetime.utcnow()}}
    )
    return JsonResponse({'message': 'Mot de passe modifié avec succès.'})


# ─── ADMIN ────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_admin
def infirmiers_list_create(request):
    if request.method == 'GET':
        infirmiers = get_all_infirmiers(
            role=request.GET.get('role'),
            statut=request.GET.get('statut'),
            search=request.GET.get('search'),
        )
        return JsonResponse([serialize_infirmier(i) for i in infirmiers], safe=False)

    if request.method == 'POST':
        data = body(request)
        for field in ['email', 'nom', 'prenom', 'password', 'role']:
            if not data.get(field):
                return JsonResponse({'error': f'Champ requis : {field}'}, status=400)
        if len(data['password']) < 8:
            return JsonResponse({'error': 'Le mot de passe doit faire au moins 8 caractères.'}, status=400)
        if data['role'] not in ['admin', 'infirmier']:
            return JsonResponse({'error': 'Rôle invalide.'}, status=400)
        if find_infirmier_by_email(data['email'].lower()):
            return JsonResponse({'error': 'Cet email est déjà utilisé.'}, status=400)

        password_clair = data['password']

        new_user = {
            'email': data['email'].strip().lower(),
            'nom': data['nom'].strip(),
            'prenom': data['prenom'].strip(),
            'password': hash_password(password_clair),
            'role': data['role'],
            'statut': 'actif',
            'telephone': data.get('telephone', ''),
            'service': data.get('service', ''),
        }
        created = create_infirmier(new_user)
        infirmier_id = str(created['_id'])

        # Générer QR code et sauvegarder
        qr_token = generer_qr_token()
        _, qr_base64 = generer_qr_code(qr_token)
        sauvegarder_qr_token(infirmier_id, qr_token, qr_base64)
        created_with_qr = find_infirmier_by_id(infirmier_id)

        # Envoyer l'email en arrière-plan
        def send_bg():
            envoyer_email_bienvenue(created_with_qr, password_clair, qr_token)
        threading.Thread(target=send_bg, daemon=True).start()

        return JsonResponse({
            **serialize_infirmier(created_with_qr),
            'email_envoye': True,
            'qr_code_base64': qr_base64,
        }, status=201)

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
@require_admin
def infirmier_detail(request, pk):
    user = find_infirmier_by_id(pk)
    if not user:
        return JsonResponse({'error': 'Utilisateur introuvable.'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_infirmier(user))

    if request.method in ['PUT', 'PATCH']:
        data = body(request)
        allowed = ['nom', 'prenom', 'email', 'role', 'service', 'telephone', 'statut']
        update_data = {k: v for k, v in data.items() if k in allowed}
        if 'email' in update_data:
            update_data['email'] = update_data['email'].strip().lower()
        return JsonResponse(serialize_infirmier(update_infirmier(pk, update_data)))

    if request.method == 'DELETE':
        if str(user['_id']) == str(request.current_user['_id']):
            return JsonResponse({'error': 'Vous ne pouvez pas supprimer votre propre compte.'}, status=400)
        delete_infirmier(pk)
        return JsonResponse({'message': 'Compte supprimé.'})

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
@require_http_methods(['PATCH'])
@require_admin
def toggle_statut(request, pk):
    user = find_infirmier_by_id(pk)
    if not user:
        return JsonResponse({'error': 'Utilisateur introuvable.'}, status=404)
    if str(user['_id']) == str(request.current_user['_id']):
        return JsonResponse({'error': 'Action impossible sur votre propre compte.'}, status=400)
    data = body(request)
    nouveau_statut = data.get('statut')
    if nouveau_statut not in ['actif', 'inactif', 'suspendu']:
        return JsonResponse({'error': 'Statut invalide.'}, status=400)
    return JsonResponse(serialize_infirmier(update_infirmier(pk, {'statut': nouveau_statut})))


@csrf_exempt
@require_http_methods(['POST'])
@require_admin
def reinitialiser_mot_de_passe(request, pk):
    user = find_infirmier_by_id(pk)
    if not user:
        return JsonResponse({'error': 'Utilisateur introuvable.'}, status=404)
    data = body(request)
    nouveau_mdp = data.get('nouveau_mot_de_passe', '')
    if len(nouveau_mdp) < 8:
        return JsonResponse({'error': 'Minimum 8 caractères.'}, status=400)
    update_infirmier(pk, {'password': hash_password(nouveau_mdp)})
    return JsonResponse({'message': f"Mot de passe de {user.get('prenom')} {user.get('nom')} réinitialisé."})


@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def statistiques(request):
    return JsonResponse(get_statistiques())

# ─── patient ────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_auth
def patients_list_create(request):

    if request.method == 'GET':
        patients = get_tous_patients()
        return JsonResponse(
            [serialize_patient(p) for p in patients],
            safe=False
        )

    if request.method == 'POST':
        data = body(request)

        # Validation des champs obligatoires
        required = ['nom', 'prenom', 'age', 'sexe',
                    'temperature', 'oxygene', 'pouls', 'symptome1']
        for field in required:
            if not str(data.get(field, '')).strip():
                return JsonResponse(
                    {'error': f'Champ requis : {field}'},
                    status=400
                )

        # Associer l'infirmier connecté au patient
        user = request.current_user
        patient_data = {
            'nom':          data['nom'].strip(),
            'prenom':       data['prenom'].strip(),
            'age':          int(data['age']),
            'sexe':         data['sexe'],
            'temperature':  float(data['temperature']),
            'oxygene':      float(data['oxygene']),
            'pouls':        int(data['pouls']),
            'symptome1':    data['symptome1'].strip(),
            'symptome2':    (data.get('symptome2') or '').strip(),
            'degre_urgence': data.get('degre_urgence'),  
            'infirmier_id':  str(user['_id']),
            'infirmier_nom': f"{user.get('prenom')} {user.get('nom')}",
}

        created = creer_patient(patient_data)
        return JsonResponse(serialize_patient(created), status=201)

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

@csrf_exempt
@require_auth
def predict_triage(request):
    if request.method != 'POST':
        return JsonResponse({'erreur': 'Méthode non autorisée'}, status=405)

    data = body(request)

    champs_requis = ['age', 'sexe', 'temperature', 'spo2', 'pouls']
    for champ in champs_requis:
        if champ not in data:
            return JsonResponse({'erreur': f'Champ manquant : {champ}'}, status=400)

    resultat = predire_niveau_urgence(data)

    if 'erreur' in resultat:
        return JsonResponse(resultat, status=500)

    return JsonResponse(resultat, status=200)

@csrf_exempt
@require_auth
def patient_detail(request, pk):
    # DELETE: supprimer un patient (fin de consultation)
    if request.method == 'DELETE':
        from .patient_service import supprimer_patient
        supprimer_patient(pk)
        return JsonResponse({'message': 'Patient supprimé.'})

    # PATCH: mettre à jour certains champs (ex: degre_urgence)
    if request.method in ['PATCH', 'PUT']:
        data = body(request)
        allowed = ['degre_urgence', 'statut', 'symptome1', 'symptome2']
        update_data = {k: v for k, v in data.items() if k in allowed}
        if not update_data:
            return JsonResponse({'error': 'Aucun champ modifiable fourni.'}, status=400)
        updated = update_patient(pk, update_data)
        if not updated:
            return JsonResponse({'error': 'Impossible de mettre à jour.'}, status=500)
        return JsonResponse(serialize_patient(updated))

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

# ───  — DASHBOARD ────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def dashboard(request):
    """
    GET /api/admin/dashboard/
    Retourne toutes les données du dashboard en un seul appel.
    """
    return JsonResponse(get_dashboard_data())


# ─── — LITS ─────────────────────────────────────────────────────────

@csrf_exempt
@require_admin
def lits_list_create(request):
    """
    GET  /api/admin/lits/           → liste tous les lits
    GET  /api/admin/lits/?statut=libre  → lits libres uniquement
    POST /api/admin/lits/           → créer un nouveau lit
    """
    if request.method == 'GET':
        statut = request.GET.get('statut')
        type_f = request.GET.get('type')
        if statut == 'libre':
            lits = get_lits_libres(type_filtre=type_f)
        else:
            lits = get_tous_lits(
                type_filtre=type_f,
                statut_filtre=statut
            )
        return JsonResponse(
            [serialize_lit(l) for l in lits],
            safe=False
        )

    if request.method == 'POST':
        data = body(request)
        for champ in ['numero', 'type', 'categorie']:
            if not data.get(champ):
                return JsonResponse(
                    {'error': f'Champ requis : {champ}'},
                    status=400
                )
        lit = creer_lit(data)
        return JsonResponse(serialize_lit(lit), status=201)

    return JsonResponse(
        {'error': 'Méthode non autorisée.'}, status=405
    )


@csrf_exempt
@require_admin
def lit_detail(request, pk):
    """
    DELETE /api/admin/lits/<id>/  → supprimer un lit
    """
    lit = get_lit_by_id(pk)
    if not lit:
        return JsonResponse(
            {'error': 'Lit introuvable.'}, status=404
        )

    if request.method == 'DELETE':
        if lit.get('statut') == 'occupe':
            return JsonResponse(
                {'error': 'Impossible de supprimer un lit occupé.'},
                status=400
            )
        supprimer_lit(pk)
        return JsonResponse({'message': 'Lit supprimé.'})

    return JsonResponse(
        {'error': 'Méthode non autorisée.'}, status=405
    )


@csrf_exempt
@require_http_methods(['GET'])
@require_auth
def lits_libres(request):
    """
    GET /api/triage/lits-libres/
    Retourne les lits libres — accessible aux infirmiers
    pour choisir un lit lors de la prise en charge.
    """
    type_f = request.GET.get('type')
    lits = get_lits_libres(type_filtre=type_f)
    return JsonResponse(
        [serialize_lit(l) for l in lits],
        safe=False
    )


# ───— ÉQUIPEMENTS ──────────────────────────────────────────────────

@csrf_exempt
@require_admin
def equipements_list_create(request):
    """
    GET  /api/admin/equipements/     → liste tous les équipements
    POST /api/admin/equipements/     → créer un nouvel équipement
    """
    if request.method == 'GET':
        eqs = get_tous_equipements()
        return JsonResponse(
            [serialize_equipement(eq) for eq in eqs],
            safe=False
        )

    if request.method == 'POST':
        data = body(request)
        if not data.get('nom'):
            return JsonResponse(
                {'error': 'Champ requis : nom'}, status=400
            )
        eq = creer_equipement(data)
        return JsonResponse(serialize_equipement(eq), status=201)

    return JsonResponse(
        {'error': 'Méthode non autorisée.'}, status=405
    )


@csrf_exempt
@require_admin
def equipement_detail(request, pk):
    """
    PATCH  /api/admin/equipements/<id>/  → modifier
    DELETE /api/admin/equipements/<id>/  → supprimer
    """
    eq = get_equipement_by_id(pk)
    if not eq:
        return JsonResponse(
            {'error': 'Équipement introuvable.'}, status=404
        )

    if request.method in ['PATCH', 'PUT']:
        data = body(request)
        allowed = ['nom', 'total', 'disponible',
                    'seuil_alerte', 'unite']
        update_data = {
            k: v for k, v in data.items() if k in allowed
        }
        updated = update_equipement(pk, update_data)
        return JsonResponse(serialize_equipement(updated))

    if request.method == 'DELETE':
        supprimer_equipement(pk)
        return JsonResponse({'message': 'Équipement supprimé.'})

    return JsonResponse(
        {'error': 'Méthode non autorisée.'}, status=405
    )


# ─── — ALERTES ──────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def alertes_list(request):
    """
    GET /api/admin/alertes/
    Retourne les alertes récentes.
    """
    limite = int(request.GET.get('limite', 50))
    alertes = get_alertes_recentes(limite)
    return JsonResponse({
        'alertes': [serialize_alerte(a) for a in alertes],
        'non_lues': get_alertes_non_lues(),
    })


@csrf_exempt
@require_http_methods(['PATCH'])
@require_admin
def alerte_marquer_lue(request, pk):
    """
    PATCH /api/admin/alertes/<id>/lue/
    Marque une alerte comme lue.
    """
    marquer_alerte_lue(pk)
    return JsonResponse({'message': 'Alerte marquée comme lue.'})


@csrf_exempt
@require_http_methods(['POST'])
@require_admin
def alertes_tout_lire(request):
    """
    POST /api/admin/alertes/tout-lire/
    Marque toutes les alertes comme lues.
    """
    marquer_toutes_lues()
    return JsonResponse({'message': 'Toutes les alertes marquées comme lues.'})


# ─── — SERVICE INFIRMIERS ───────────────────────────────────────────

@csrf_exempt
@require_http_methods(['PATCH'])
@require_admin
def toggle_service_infirmier(request, pk):
    """
    PATCH /api/admin/infirmiers/<id>/service/
    Met un infirmier en service ou hors service.
    Body: { "en_service": true/false }
    """
    user = find_infirmier_by_id(pk)
    if not user:
        return JsonResponse(
            {'error': 'Utilisateur introuvable.'}, status=404
        )
    data = body(request)
    en_service = data.get('en_service', False)
    updated = toggle_service(pk, en_service)
    return JsonResponse(serialize_infirmier(updated))


@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def infirmiers_en_service(request):
    """
    GET /api/admin/infirmiers-en-service/
    Retourne la liste des infirmiers actuellement en service.
    """
    en_service = get_infirmiers_en_service()
    return JsonResponse(
        [serialize_infirmier(i) for i in en_service],
        safe=False
    )


# ───— PRISE EN CHARGE PATIENT ──────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
@require_auth
def prendre_en_charge_patient(request, pk):
    """
    POST /api/triage/patients/<id>/prendre-en-charge/
    Body: { "lit_id": "abc123" }

    1. Le patient passe de 'en_attente' à 'en_consultation'
    2. Le lit choisi passe de 'libre' à 'occupe'
    """
    patient = get_patient_by_id(pk)
    if not patient:
        return JsonResponse(
            {'error': 'Patient introuvable.'}, status=404
        )
    if patient.get('statut') != 'en_attente':
        return JsonResponse(
            {'error': 'Ce patient n\'est plus en attente.'},
            status=400
        )

    data = body(request)
    lit_id = data.get('lit_id')
    if not lit_id:
        return JsonResponse(
            {'error': 'Champ requis : lit_id'}, status=400
        )

    # Vérifier que le lit est libre
    lit = get_lit_by_id(lit_id)
    if not lit:
        return JsonResponse(
            {'error': 'Lit introuvable.'}, status=404
        )
    if lit.get('statut') != 'libre':
        return JsonResponse(
            {'error': 'Ce lit est déjà occupé.'}, status=400
        )

    # 1. Occuper le lit
    nom_patient = f"{patient.get('prenom', '')} {patient.get('nom', '')}"
    occuper_lit(lit_id, pk, nom_patient)

    # 2. Mettre à jour le patient
    updated = prendre_en_charge(
        pk, lit_id, lit.get('numero', '')
    )

    return JsonResponse(serialize_patient(updated))


@csrf_exempt
@require_http_methods(['POST'])
@require_auth
def terminer_consultation(request, pk):
    """
    POST /api/triage/patients/<id>/terminer/

    1. Le patient passe à 'termine'
    2. Le lit est automatiquement libéré
    """
    patient = get_patient_by_id(pk)
    if not patient:
        return JsonResponse(
            {'error': 'Patient introuvable.'}, status=404
        )
    if patient.get('statut') not in ['en_attente', 'en_consultation']:
        return JsonResponse(
            {'error': 'Ce patient est déjà terminé.'},
            status=400
        )

    # 1. Libérer le lit si le patient en avait un
    lit_id = patient.get('lit_id')
    if lit_id:
        liberer_lit_par_patient(pk)

    # 2. Archiver le patient
    updated = terminer_patient(pk)

    return JsonResponse(serialize_patient(updated))

# ─── PROFIL INFIRMIER ─────────────────────────────────────────────────────────

@csrf_exempt
@require_auth
def mon_profil(request):
    """
    GET  /api/auth/profil/ → données du profil
    PATCH /api/auth/profil/ → modifier casier, telephone
    """
    user = request.current_user

    if request.method == 'GET':
        data = serialize_infirmier(user)
        data['numero_casier'] = user.get('numero_casier', '')
        return JsonResponse(data)

    if request.method in ['PATCH', 'PUT']:
        data = body(request)
        allowed = ['numero_casier', 'telephone']
        update_data = {k: v for k, v in data.items() if k in allowed}
        if update_data:
            updated = update_infirmier(str(user['_id']), update_data)
            result = serialize_infirmier(updated)
            result['numero_casier'] = updated.get('numero_casier', '')
            return JsonResponse(result)
        return JsonResponse({'error': 'Aucun champ modifiable.'}, status=400)

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
@require_auth
def mes_remarques(request):
    """
    GET  /api/auth/remarques/ → mes remarques
    POST /api/auth/remarques/ → soumettre une remarque
    """
    user = request.current_user

    if request.method == 'GET':
        remarques = get_remarques_by_infirmier(str(user['_id']))
        return JsonResponse(
            [serialize_remarque(r) for r in remarques],
            safe=False
        )

    if request.method == 'POST':
        data = body(request)
        if not data.get('message', '').strip():
            return JsonResponse(
                {'error': 'Le message est requis.'}, status=400
            )
        remarque_data = {
            'infirmier_id': str(user['_id']),
            'infirmier_nom': f"{user.get('prenom', '')} {user.get('nom', '')}",
            'type': data.get('type', 'remarque'),
            'sujet': data.get('sujet', '').strip(),
            'message': data['message'].strip(),
        }
        created = create_remarque(remarque_data)
        return JsonResponse(serialize_remarque(created), status=201)

    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


# ─── ADMIN — REMARQUES ───────────────────────────────────────────────────────

@csrf_exempt
@require_admin
def admin_remarques(request):
    """
    GET /api/admin/remarques/ → toutes les remarques
    """
    if request.method == 'GET':
        remarques = get_toutes_remarques()
        return JsonResponse(
            [serialize_remarque(r) for r in remarques],
            safe=False
        )
    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


# ─── PLANNING DU SERVICE ──────────────────────────────────────────────────────

@csrf_exempt
@require_admin
def planning_semaine(request):
    """
    GET /api/admin/planning/?semaine=2026-04-20
    Retourne le planning de la semaine.
    """
    if request.method == 'GET':
        semaine = request.GET.get('semaine')
        plannings = get_planning_semaine(semaine)
        return JsonResponse(
            [serialize_planning(p) for p in plannings],
            safe=False
        )
    return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)


@csrf_exempt
@require_admin
def planning_toggle(request):
    """
    POST /api/admin/planning/toggle/
    Body: { "infirmier_id": "...", "date": "2026-04-21", "creneau": "matin" }
    Ajoute ou retire un infirmier d'un créneau.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée.'}, status=405)

    data = body(request)
    infirmier_id = data.get('infirmier_id')
    date_str = data.get('date')
    creneau = data.get('creneau')

    if not all([infirmier_id, date_str, creneau]):
        return JsonResponse({'error': 'Champs requis : infirmier_id, date, creneau'}, status=400)

    if creneau not in ['matin', 'aprem', 'nuit']:
        return JsonResponse({'error': 'Créneau invalide. Utilisez: matin, après-midi ou nuit'}, status=400)

    # Vérifier si déjà planifié
    from .mongo_service import planning_collection
    from datetime import datetime as dt
    date_obj = dt.strptime(date_str, '%Y-%m-%d')
    existe = planning_collection().find_one({
        'infirmier_id': infirmier_id,
        'date': date_obj,
        'creneau': creneau
    })

    if existe:
        supprimer_planning(infirmier_id, date_str, creneau)
        return JsonResponse({'action': 'removed', 'message': 'Créneau retiré.'})
    else:
        infirmier = find_infirmier_by_id(infirmier_id)
        if not infirmier:
            return JsonResponse({'error': 'Infirmier introuvable.'}, status=404)
        nom = f"{infirmier.get('prenom', '')} {infirmier.get('nom', '')}"
        ajouter_planning(infirmier_id, nom, date_str, creneau)
        return JsonResponse({'action': 'added', 'message': 'Créneau ajouté.'})
    
@csrf_exempt
@require_http_methods(['PATCH'])
@require_admin
def admin_remarque_lue(request, pk):
    """Marque une remarque comme lue"""
    marquer_remarque_lue(pk)
    return JsonResponse({'message': 'Remarque marquée comme lue.'})

@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def historique_patients(request):
    """GET /api/admin/historique/"""
    limite = int(request.GET.get('limite', 50))
    patients = get_patients_termines(limite)
    return JsonResponse(
        [serialize_patient(p) for p in patients],
        safe=False
    )


@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def statistiques_avancees(request):

    """GET /api/admin/statistiques-avancees/"""
    stats = get_statistiques_avancees()
    return JsonResponse(stats)

@csrf_exempt
@require_http_methods(['GET'])
@require_auth
def mon_planning(request):

    """
    GET /api/auth/mon-planning/
    Retourne le planning de la semaine de l'infirmier connecté.
    """
    user = request.current_user
    user_id = str(user['_id'])
    plannings = get_planning_semaine()

    # Filtrer pour cet infirmier
    mon_planning = [
        serialize_planning(p) for p in plannings
        if p.get('infirmier_id') == user_id
    ]

    return JsonResponse(mon_planning, safe=False)

@csrf_exempt
@require_http_methods(['GET'])
@require_admin
def export_historique_pdf(request):
    
    mois_str = request.GET.get('mois')  # format: YYYY-MM
    if not mois_str:
        return JsonResponse({'error': 'Paramètre mois requis (YYYY-MM)'}, status=400)

    try:
        annee, mois = mois_str.split('-')
        annee, mois = int(annee), int(mois)
    except:
        return JsonResponse({'error': 'Format invalide. Utilisez YYYY-MM'}, status=400)

    from datetime import datetime, timedelta
    import calendar

    debut = datetime(annee, mois, 1)
    dernier_jour = calendar.monthrange(annee, mois)[1]
    fin = datetime(annee, mois, dernier_jour, 23, 59, 59)

    # Patients du mois
    patients = list(
        patient_collection()
        .find({'date_creation': {'$gte': debut, '$lte': fin}})
        .sort('date_creation', 1)
    )

    # Distribution par niveau
    distribution = {}
    for n in range(1, 6):
        distribution[f'P{n}'] = len([p for p in patients if p.get('degre_urgence') == n])

    # Temps d'attente moyen par niveau
    temps_attente = {}
    for n in range(1, 6):
        patients_niveau = [
            p for p in patients
            if p.get('degre_urgence') == n
            and p.get('date_creation')
            and p.get('date_prise_en_charge')
        ]
        if patients_niveau:
            total_min = sum(
                (p['date_prise_en_charge'] - p['date_creation']).total_seconds() / 60
                for p in patients_niveau
            )
            temps_attente[f'P{n}'] = round(total_min / len(patients_niveau), 1)

    # Taux correction
    total_evalues = len([p for p in patients if p.get('degre_urgence') is not None])
    total_corriges = len([p for p in patients if p.get('correction_manuelle')])
    taux_correction = round(total_corriges / total_evalues * 100, 1) if total_evalues > 0 else 0

    # Affluence par jour du mois
    affluence_jours = []
    for jour in range(1, dernier_jour + 1):
        d = datetime(annee, mois, jour)
        d_fin = d + timedelta(days=1)
        count = len([p for p in patients if d <= p.get('date_creation', datetime.min) < d_fin])
        affluence_jours.append({
            'jour': jour,
            'date': d.strftime('%d/%m'),
            'count': count
        })

    # Sérialiser patients
    patients_data = []
    for p in patients:
        patients_data.append({
            'nom': p.get('nom', ''),
            'prenom': p.get('prenom', ''),
            'age': p.get('age', ''),
            'sexe': p.get('sexe', ''),
            'degre_urgence': p.get('degre_urgence'),
            'infirmier_nom': p.get('infirmier_nom', ''),
            'lit_numero': p.get('lit_numero', ''),
            'correction_manuelle': p.get('correction_manuelle', False),
            'date_creation': p['date_creation'].strftime('%d/%m/%Y %H:%M') if p.get('date_creation') else '',
        })

    mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

    return JsonResponse({
        'mois_label': f'{mois_noms[mois]} {annee}',
        'total_patients': len(patients),
        'distribution': distribution,
        'temps_attente': temps_attente,
        'taux_correction': taux_correction,
        'total_corriges': total_corriges,
        'total_evalues': total_evalues,
        'affluence_jours': affluence_jours,
        'patients': patients_data,
    })

# ══════════════════════════════════════════
# IoT — Réception des données du bracelet
# ══════════════════════════════════════════

@csrf_exempt
@require_auth
def iot_vitals_receive(request):
    """POST /api/iot/vitals/ — Reçoit les données du bracelet ESP32"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    data = json.loads(request.body)
    user = request.current_user

    # Validation des plages physiologiques
    pouls = data.get('pouls', 0)
    oxygene = data.get('oxygene', 0)
    temperature = data.get('temperature', 0)
    rr = data.get('rr', 0)
    sbp = data.get('sbp', 0)
    dbp = data.get('dbp', 0)

    if pouls == 0 and oxygene == 0 and temperature == 0:
        return JsonResponse({'error': 'Aucune mesure valide'}, status=400)

    from datetime import datetime

    vitals = {
        'infirmier_id': str(user['_id']),
        'pouls': pouls,
        'oxygene': oxygene,
        'temperature': temperature,
        'rr': rr,
        'sbp': sbp,
        'dbp': dbp,
        'source': data.get('source', 'iot_bracelet'),
        'qualite': data.get('qualite', 0),
        'timestamp': datetime.utcnow()
    }

    # Upsert : écrase la dernière mesure de cet infirmier
    from django.conf import settings
    db = settings.MONGO_DB
    db.iot_vitaux.update_one(
        {'infirmier_id': str(user['_id'])},
        {'$set': vitals},
        upsert=True
    )

    return JsonResponse({'status': 'ok', 'message': 'Données reçues'}, status=201)


@csrf_exempt
@require_auth
def iot_vitals_last(request):
    """GET /api/iot/vitals/last/ — Retourne les dernières mesures"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    user = request.current_user

    from django.conf import settings
    db = settings.MONGO_DB
    doc = db.iot_vitaux.find_one(
        {'infirmier_id': str(user['_id'])},
        {'_id': 0, 'infirmier_id': 0}
    )

    if not doc:
        return JsonResponse({'error': 'Aucune donnée IoT disponible'}, status=404)

    # Convertir datetime pour JSON
    if 'timestamp' in doc:
        doc['timestamp'] = doc['timestamp'].isoformat()

    return JsonResponse(doc, status=200)