import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Infirmier } from './auth.service';
import { API_BASE } from '../api.config';

export interface StatistiquesAdmin {
  total: number;
  actifs: number;
  inactifs: number;
  suspendus: number;
  admins: number;
  infirmiers: number;
}

export interface CreateInfirmierDto {
  email: string;
  nom: string;
  prenom: string;
  password: string;
  role: 'admin' | 'infirmier';
  telephone?: string;
  service?: string;
}

@Injectable({ providedIn: 'root' })
export class InfirmiersService {
  private readonly ADMIN = `${API_BASE}/admin`;

  constructor(private http: HttpClient) {}

  getAll(filtres?: { role?: string; statut?: string; search?: string }): Observable<Infirmier[]> {
    let params = new HttpParams();
    if (filtres?.role)   params = params.set('role', filtres.role);
    if (filtres?.statut) params = params.set('statut', filtres.statut);
    if (filtres?.search) params = params.set('search', filtres.search);
    return this.http.get<Infirmier[]>(`${this.ADMIN}/infirmiers/`, { params });
  }

  getById(id: string): Observable<Infirmier> {
    return this.http.get<Infirmier>(`${this.ADMIN}/infirmiers/${id}/`);
  }

  create(data: CreateInfirmierDto): Observable<any> {
    return this.http.post<any>(`${this.ADMIN}/infirmiers/`, data);
  }

  update(id: string, data: Partial<Infirmier>): Observable<any> {
    return this.http.patch<any>(`${this.ADMIN}/infirmiers/${id}/`, data);
  }

  delete(id: string): Observable<any> {
    return this.http.delete(`${this.ADMIN}/infirmiers/${id}/`);
  }

  toggleStatut(id: string, statut: 'actif' | 'inactif' | 'suspendu'): Observable<Infirmier> {
    return this.http.patch<Infirmier>(`${this.ADMIN}/infirmiers/${id}/statut/`, { statut });
  }

  reinitialiserMdp(id: string, nouveau_mot_de_passe: string): Observable<any> {
    return this.http.post(`${this.ADMIN}/infirmiers/${id}/reinitialiser-mdp/`, { nouveau_mot_de_passe });
  }

  getStatistiques(): Observable<StatistiquesAdmin> {
    return this.http.get<StatistiquesAdmin>(`${this.ADMIN}/statistiques/`);
  }
}