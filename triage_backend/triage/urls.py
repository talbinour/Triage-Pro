from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────
    path('auth/login/', views.login, name='login'),
    path('auth/qr-login/', views.qr_login, name='qr-login'),
    path('auth/me/', views.me, name='me'),
    path('auth/changer-mot-de-passe/',
         views.changer_mot_de_passe, name='changer-mdp'),
    path('auth/profil/', views.mon_profil, name='mon-profil'),
    path('auth/remarques/', views.mes_remarques, name='mes-remarques'),
    path('auth/mon-planning/', views.mon_planning, name='mon-planning'),
    # ── Admin — Infirmiers ────────────────────
    path('admin/infirmiers/',
         views.infirmiers_list_create, name='infirmiers-list'),
    path('admin/infirmiers/<str:pk>/',
         views.infirmier_detail, name='infirmier-detail'),
    path('admin/infirmiers/<str:pk>/statut/',
         views.toggle_statut, name='toggle-statut'),
    path('admin/infirmiers/<str:pk>/reinitialiser-mdp/',
         views.reinitialiser_mot_de_passe, name='reinit-mdp'),
    path('admin/statistiques/',
         views.statistiques, name='statistiques'),
    path('admin/remarques/', views.admin_remarques, name='admin-remarques'),
     path('admin/remarques/<str:pk>/lue/', views.admin_remarque_lue, name='remarque-lue'),
    path('admin/planning/', views.planning_semaine, name='planning'),
    path('admin/planning/toggle/', views.planning_toggle, name='planning-toggle'),
    # ── Admin — : Service ────────────
    path('admin/infirmiers/<str:pk>/service/',
         views.toggle_service_infirmier, name='toggle-service'),
    path('admin/infirmiers-en-service/',
         views.infirmiers_en_service, name='infirmiers-en-service'),

    # ── Admin —: Dashboard ──────────
    path('admin/dashboard/',
         views.dashboard, name='dashboard'),
    path('admin/historique/', views.historique_patients, name='historique'),
    path('admin/statistiques-avancees/', views.statistiques_avancees, name='stats-avancees'),
    path('admin/export-historique/', views.export_historique_pdf, name='export-historique'),

    # ── Admin —: Lits ───────────────
    path('admin/lits/',
         views.lits_list_create, name='lits-list'),
    path('admin/lits/<str:pk>/',
         views.lit_detail, name='lit-detail'),

    # ── Admin —: Équipements ────────
    path('admin/equipements/',
         views.equipements_list_create, name='equipements-list'),
    path('admin/equipements/<str:pk>/',
         views.equipement_detail, name='equipement-detail'),

    # ── Admin —: Alertes ────────────
    path('admin/alertes/',
         views.alertes_list, name='alertes-list'),
    path('admin/alertes/<str:pk>/lue/',
         views.alerte_marquer_lue, name='alerte-lue'),
    path('admin/alertes/tout-lire/',
         views.alertes_tout_lire, name='alertes-tout-lire'),

    # ── Triage — Patients ─────────────────────
    path('triage/patients/',
         views.patients_list_create, name='patients'),
    path('triage/predict/',
         views.predict_triage, name='predict_triage'),
    path('triage/patients/<str:pk>/',
         views.patient_detail, name='patient_detail'),

    # ── Triage —: Prise en charge ───
    path('triage/lits-libres/',
         views.lits_libres, name='lits-libres'),
    path('triage/patients/<str:pk>/prendre-en-charge/',
         views.prendre_en_charge_patient,
         name='prendre-en-charge'),
    path('triage/patients/<str:pk>/terminer/',
         views.terminer_consultation,
         name='terminer-consultation'),

     # Routes IoT (accessible via /api/triage/iot/...)
     path('iot/vitals/', views.iot_vitals_receive, name='iot_vitals_triage'),
     path('iot/vitals/last/', views.iot_vitals_last, name='iot_vitals_last_triage'),
]