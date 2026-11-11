import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { API_BASE } from '../api.config';

export interface Infirmier {
  id: string;
  email: string;
  nom: string;
  prenom: string;
  nom_complet: string;
  role: 'admin' | 'infirmier';
  statut: 'actif' | 'inactif' | 'suspendu';
  telephone?: string;
  service?: string;
  date_creation?: string;
  en_service?: boolean;   
  debut_service?: string; 
  qr_code_base64?: string;
  numero_casier?: string;
}

export interface LoginResponse {
  token: string;
  user: Infirmier;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'triage_jwt';
  private readonly USER_KEY = 'triage_user';

  currentUser$ = new BehaviorSubject<Infirmier | null>(this.getStoredUser());

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${API_BASE}/auth/login/`, { email, password }).pipe(
      tap(res => {
        localStorage.setItem(this.TOKEN_KEY, res.token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(res.user));
        this.currentUser$.next(res.user);
      })
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUser$.next(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isAdmin(): boolean {
    return this.currentUser$.value?.role === 'admin';
  }

  private getStoredUser(): Infirmier | null {
    try {
      const raw = localStorage.getItem(this.USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }
  getMonProfil(): Observable<Infirmier> {
    return this.http.get<Infirmier>(`${API_BASE}/auth/profil/`);
  }

  updateProfil(data: any): Observable<Infirmier> {
    return this.http.patch<Infirmier>(`${API_BASE}/auth/profil/`, data);
  }

  getMesRemarques(): Observable<any[]> {
    return this.http.get<any[]>(`${API_BASE}/auth/remarques/`);
  }

  envoyerRemarque(data: any): Observable<any> {
    return this.http.post(`${API_BASE}/auth/remarques/`, data);
  }

  changerMotDePasse(ancien: string, nouveau: string, confirmation: string): Observable<any> {
    return this.http.post(`${API_BASE}/auth/changer-mot-de-passe/`, {
      ancien_mot_de_passe: ancien,
      nouveau_mot_de_passe: nouveau,
      confirmation
    });
  }
  getMonPlanning(): Observable<any[]> {
    return this.http.get<any[]>(`${API_BASE}/auth/mon-planning/`);
  }
}