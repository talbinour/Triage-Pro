import joblib
import numpy as np
import os

# ── Chemins des fichiers .pkl ──────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE_DIR, 'triage_model_final.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'triage_scaler_final.pkl')

# ── Chargement unique au démarrage ────────────
try:
    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✓ Modèle IA chargé avec succès")
except Exception as e:
    model  = None
    scaler = None
    print(f"✗ Erreur chargement modèle : {e}")

# ── Labels KTAS ───────────────────────────────
KTAS_LABELS = {
    1: {"niveau": "P1", "label": "Immédiat",    "couleur": "#c0392b"},
    2: {"niveau": "P2", "label": "Très urgent", "couleur": "#e67e22"},
    3: {"niveau": "P3", "label": "Urgent",      "couleur": "#f1c40f"},
    4: {"niveau": "P4", "label": "Peu urgent",  "couleur": "#27ae60"},
    5: {"niveau": "P5", "label": "Non urgent",  "couleur": "#2980b9"},
}

# ── Ordre exact des features du modèle ────────
FEATURES = [
    'Sex', 'Age', 'Arrival mode', 'Injury',
    'Mental', 'Pain', 'NRS_pain',
    'SBP', 'DBP', 'HR', 'RR', 'BT', 'Saturation'
]


def predire_niveau_urgence(data: dict) -> dict:
    """
    Prédit le niveau d'urgence KTAS à partir
    des données cliniques du patient.

    Paramètres attendus dans data :
        age        : int   — âge du patient
        sexe       : int   — 1=Femme, 2=Homme
        temperature: float — température corporelle (°C)
        spo2       : float — saturation O2 (%)
        pouls      : float — fréquence cardiaque (bpm)

    Paramètres optionnels (valeurs par défaut sinon) :
        arrival_mode : int   — 1=Marche, 2=Ambulance,
                               3=Véhicule, 4=Ambulance privée
        injury       : int   — 1=Non, 2=Oui
        mental       : int   — 1=Alerte, 2=Verbal,
                               3=Douleur, 4=Inconscient
        pain         : int   — 0=Non, 1=Oui
        nrs_pain     : float — score douleur 0-10
        sbp          : float — pression systolique
        dbp          : float — pression diastolique
        rr           : float — fréquence respiratoire

    Retourne :
        dict avec niveau, label, couleur, confiance,
        probabilités et recommandation
    """

    if model is None or scaler is None:
        return {"erreur": "Modèle IA non disponible"}

    try:
        # ── Construction du vecteur de features ───
        features_vector = [
            int(data.get('sexe', 1)),
            int(data.get('age', 50)),
            int(data.get('arrival_mode', 3)),
            int(data.get('injury', 1)),
            int(data.get('mental', 1)),
            int(data.get('pain', 0)),        # ← 0 par défaut (pas douleur)
            float(data.get('nrs_pain', 0.0)), # ← 0 par défaut
            float(data.get('sbp', 120.0)),   # ← valeur normale
            float(data.get('dbp', 75.0)),    # ← valeur normale
            float(data.get('pouls', 80.0)),
            float(data.get('rr', 16.0)),     # ← valeur normale
            float(data.get('temperature', 37.0)),
            float(data.get('spo2', 98.0)),
        ]

        # ── Normalisation ─────────────────────────
        X = np.array(features_vector).reshape(1, -1)
        X_scaled = scaler.transform(X)

        # ── Prédiction ────────────────────────────
        prediction  = int(model.predict(X_scaled)[0])
        probabilites = model.predict_proba(X_scaled)[0]
        confiance   = float(probabilites.max() * 100)

        # ── Informations du niveau ─────────────────
        info = KTAS_LABELS.get(prediction, KTAS_LABELS[3])

        # ── Recommandation textuelle ───────────────
        recommandations = {
            1: "Prise en charge immédiate requise — urgence vitale",
            2: "Patient à voir dans les 10 minutes",
            3: "Patient à voir dans les 30 minutes",
            4: "Patient à voir dans l'heure",
            5: "Patient non urgent — peut attendre",
        }

        # ── Probabilités par niveau ───────────────
        proba_dict = {
            f"P{i+1}": round(float(p) * 100, 1)
            for i, p in enumerate(probabilites)
        }

        return {
            "niveau"         : info["niveau"],
            "label"          : info["label"],
            "couleur"        : info["couleur"],
            "confiance"      : round(confiance, 1),
            "recommandation" : recommandations[prediction],
            "probabilites"   : proba_dict,
            "necessite_questions": confiance < 85.0,
        }

    except Exception as e:
        return {"erreur": f"Erreur prédiction : {str(e)}"}