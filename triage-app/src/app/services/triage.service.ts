import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE } from '../api.config';

export interface Patient {
  id:            string;
  nom:           string;
  prenom:        string;
  age:           number;
  sexe:          string;
  temperature:   number;
  oxygene:       number;
  pouls:         number;
  symptome1:     string;
  symptome2:     string;
  degre_urgence: number | null;
  statut:        string;
  infirmier_nom: string;
  date_creation: string;
  lit_id?: string;
  lit_numero?: string;
}

export interface PredictionResult {
  niveau:              string;
  label:               string;
  couleur:             string;
  confiance:           number;
  recommandation:      string;
  probabilites:        { [key: string]: number };
  necessite_questions: boolean;
}

export interface PatientIA {
  age:         number;
  sexe:        number;
  temperature: number;
  spo2:        number;
  pouls:       number;
}

@Injectable({ providedIn: 'root' })
export class TriageService {

  private readonly API = `${API_BASE}/triage`;

  constructor(private http: HttpClient) {}

  creerPatient(data: Partial<Patient>): Observable<Patient> {
    return this.http.post<Patient>(`${this.API}/patients/`, data);
  }

  getTousPatients(): Observable<Patient[]> {
    return this.http.get<Patient[]>(`${this.API}/patients/`);
  }

  predictTriage(data: PatientIA): Observable<PredictionResult> {
    return this.http.post<PredictionResult>(`${this.API}/predict/`, data);
  }

  // ── Supprimer un patient (consultation terminée) ──
  supprimerPatient(id: string): Observable<any> {
    return this.http.delete(`${this.API}/patients/${id}/`);
  }

  updatePatient(id: string, data: Partial<Patient>): Observable<Patient> {
    return this.http.patch<Patient>(`${this.API}/patients/${id}/`, data);
  }
  // Prise en charge ──────────
  getLitsLibres(type?: string): Observable<any[]> {
    let url = `${API_BASE}/triage/lits-libres/`;
    if (type) url += `?type=${type}`;
    return this.http.get<any[]>(url);
  }

  prendreEnCharge(patientId: string, litId: string): Observable<Patient> {
    return this.http.post<Patient>(
      `${this.API}/patients/${patientId}/prendre-en-charge/`,
      { lit_id: litId }
    );
  }

  terminerConsultation(patientId: string): Observable<Patient> {
    return this.http.post<Patient>(
      `${this.API}/patients/${patientId}/terminer/`,
      {}
    );
  }
  getIoTVitals(): Observable<any> {
  return this.http.get<any>(`${API_BASE}/iot/vitals/last/`);
}
}
