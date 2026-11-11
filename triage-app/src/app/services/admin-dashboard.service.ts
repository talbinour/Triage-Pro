import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE } from '../api.config';

// ── Interfaces ──────────────────────────────

export interface DashboardData {
  patients: {
    par_niveau: { [key: string]: number };
    total_attente: number;
    en_consultation: number;
    termines_aujourdhui: number;
  };
  lits: ResumeList[];
  equipements: Equipement[];
  personnel: { en_service: number };
  alertes: Alerte[];
  alertes_non_lues: number;
}

export interface ResumeList {
  type: string;
  categorie: string;
  total: number;
  libres: number;
  occupes: number;
}

export interface Lit {
  id: string;
  numero: string;
  type: string;
  categorie: string;
  statut: 'libre' | 'occupe';
  patient_id: string;
  patient_nom: string;
  date_occupation: string | null;
}

export interface Equipement {
  id: string;
  nom: string;
  total: number;
  disponible: number;
  seuil_alerte: number;
  unite: string;
  date_modification: string;
}

export interface Alerte {
  id: string;
  type: string;
  severite: 'critique' | 'avertissement' | 'info';
  message: string;
  details: string;
  lue: boolean;
  date: string;
}

@Injectable({ providedIn: 'root' })
export class AdminDashboardService {

  private readonly ADMIN = `${API_BASE}/admin`;
  private readonly TRIAGE = `${API_BASE}/triage`;

  constructor(private http: HttpClient) {}

  // ── Dashboard ────────────────────────────
  getDashboard(): Observable<DashboardData> {
    return this.http.get<DashboardData>(
      `${this.ADMIN}/dashboard/`
    );
  }

  // ── Lits ─────────────────────────────────
  getLits(statut?: string, type?: string): Observable<Lit[]> {
    let url = `${this.ADMIN}/lits/`;
    const params: string[] = [];
    if (statut) params.push(`statut=${statut}`);
    if (type) params.push(`type=${type}`);
    if (params.length) url += '?' + params.join('&');
    return this.http.get<Lit[]>(url);
  }

  creerLit(data: Partial<Lit>): Observable<Lit> {
    return this.http.post<Lit>(
      `${this.ADMIN}/lits/`, data
    );
  }

  supprimerLit(id: string): Observable<any> {
    return this.http.delete(
      `${this.ADMIN}/lits/${id}/`
    );
  }

  getLitsLibres(type?: string): Observable<Lit[]> {
    let url = `${this.TRIAGE}/lits-libres/`;
    if (type) url += `?type=${type}`;
    return this.http.get<Lit[]>(url);
  }

  // ── Équipements ──────────────────────────
  getEquipements(): Observable<Equipement[]> {
    return this.http.get<Equipement[]>(
      `${this.ADMIN}/equipements/`
    );
  }

  creerEquipement(data: Partial<Equipement>): Observable<Equipement> {
    return this.http.post<Equipement>(
      `${this.ADMIN}/equipements/`, data
    );
  }

  updateEquipement(id: string, data: Partial<Equipement>): Observable<Equipement> {
    return this.http.patch<Equipement>(
      `${this.ADMIN}/equipements/${id}/`, data
    );
  }

  supprimerEquipement(id: string): Observable<any> {
    return this.http.delete(
      `${this.ADMIN}/equipements/${id}/`
    );
  }

  // ── Alertes ──────────────────────────────
  getAlertes(limite?: number): Observable<{alertes: Alerte[], non_lues: number}> {
    let url = `${this.ADMIN}/alertes/`;
    if (limite) url += `?limite=${limite}`;
    return this.http.get<{alertes: Alerte[], non_lues: number}>(url);
  }

  marquerAlerteLue(id: string): Observable<any> {
    return this.http.patch(
      `${this.ADMIN}/alertes/${id}/lue/`, {}
    );
  }

  marquerToutesLues(): Observable<any> {
    return this.http.post(
      `${this.ADMIN}/alertes/tout-lire/`, {}
    );
  }

  // ── Service infirmiers ───────────────────
  toggleService(id: string, en_service: boolean): Observable<any> {
    return this.http.patch(
      `${this.ADMIN}/infirmiers/${id}/service/`,
      { en_service }
    );
  }

  getInfirmiersEnService(): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.ADMIN}/infirmiers-en-service/`
    );
  }

  // ── Prise en charge patient ──────────────
  prendreEnCharge(patientId: string, litId: string): Observable<any> {
    return this.http.post(
      `${this.TRIAGE}/patients/${patientId}/prendre-en-charge/`,
      { lit_id: litId }
    );
  }

  terminerConsultation(patientId: string): Observable<any> {
    return this.http.post(
      `${this.TRIAGE}/patients/${patientId}/terminer/`,
      {}
    );
  }
  // ── Remarques (admin) ────────────────────
  getRemarques(): Observable<any[]> {
    return this.http.get<any[]>(`${this.ADMIN}/remarques/`);
  }

  repondreRemarque(id: string, reponse: string): Observable<any> {
    return this.http.patch(`${this.ADMIN}/remarques/${id}/repondre/`, { reponse });
  }
  marquerRemarqueLue(id: string): Observable<any> {
    return this.http.patch(`${this.ADMIN}/remarques/${id}/lue/`, {});
  }
  // ── Planning ─────────────────────────────
  getPlanning(semaine?: string): Observable<any[]> {
    let url = `${this.ADMIN}/planning/`;
    if (semaine) url += `?semaine=${semaine}`;
    return this.http.get<any[]>(url);
  }

  togglePlanning(infirmier_id: string, date: string, creneau: string): Observable<any> {
    return this.http.post(`${this.ADMIN}/planning/toggle/`, {
      infirmier_id, date, creneau
    });
  }
  // ── Statistiques avancées ────────────────
  getHistorique(limite?: number): Observable<any[]> {
    let url = `${this.ADMIN}/historique/`;
    if (limite) url += `?limite=${limite}`;
    return this.http.get<any[]>(url);
  }

  getStatistiquesAvancees(): Observable<any> {
    return this.http.get<any>(`${this.ADMIN}/statistiques-avancees/`);
  }
  
  getExportHistorique(mois: string): Observable<any> {
    return this.http.get<any>(`${this.ADMIN}/export-historique/?mois=${mois}`);
  }

}