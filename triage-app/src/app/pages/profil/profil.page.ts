import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule, ToastController } from '@ionic/angular';
import { Router } from '@angular/router';
import { AuthService, Infirmier } from '../../services/auth.service';

@Component({
  selector: 'app-profil',
  templateUrl: './profil.page.html',
  styleUrls: ['./profil.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule],
})
export class ProfilPage implements OnInit {

  currentUser: Infirmier | null = null;
  profilData: any = null;
  profilLoading = false;

  mesRemarques: any[] = [];
  remarquesLoading = false;

  numeroCasier = '';

  showMdpModal = false;
  mdpForm = { ancien: '', nouveau: '', confirmation: '' };
  mdpError = '';
  mdpLoading = false;

  showRemarqueModal = false;
  remarqueForm = { type: 'remarque', sujet: '', message: '' };
  remarqueLoading = false;
  // Planning
  monPlanning: any[] = [];
  planningLoading = false;
  showPlanningBanner = true;

  constructor(
    private auth: AuthService,
    private toastCtrl: ToastController,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.currentUser = this.auth.currentUser$.value;
    this.loadProfil();
  }

  loadProfil(): void {
    this.profilLoading = true;
    this.auth.getMonProfil().subscribe({
      next: (data) => {
        this.profilData = data;
        this.numeroCasier = data.numero_casier || '';
        this.profilLoading = false;
      },
      error: () => { this.profilLoading = false; }
    });
    this.loadRemarques();
    this.loadMonPlanning();
  }

  loadRemarques(): void {
    this.remarquesLoading = true;
    this.auth.getMesRemarques().subscribe({
      next: (data) => {
        // Ne montrer que les remarques non lues (non traitées)
        this.mesRemarques = data.filter((r: any) => !r.lue);
        this.remarquesLoading = false;
      },
      error: () => { this.remarquesLoading = false; }
    });
  }

  sauvegarderCasier(): void {
    this.auth.updateProfil({ numero_casier: this.numeroCasier }).subscribe({
      next: () => this.showToast('Numéro de casier enregistré ✓', 'success'),
      error: () => this.showToast('Erreur', 'danger')
    });
  }

  openRemarqueModal(): void {
    this.remarqueForm = { type: 'remarque', sujet: '', message: '' };
    this.showRemarqueModal = true;
  }

  envoyerRemarque(): void {
    if (!this.remarqueForm.message.trim()) return;
    this.remarqueLoading = true;
    this.auth.envoyerRemarque(this.remarqueForm).subscribe({
      next: () => {
        this.remarqueLoading = false;
        this.showRemarqueModal = false;
        this.loadRemarques();
        this.showToast('Remarque envoyée ✓', 'success');
      },
      error: () => { this.remarqueLoading = false; this.showToast('Erreur', 'danger'); }
    });
  }

  openMdpModal(): void {
    this.mdpForm = { ancien: '', nouveau: '', confirmation: '' };
    this.mdpError = '';
    this.showMdpModal = true;
  }

  changerMdp(): void {
    if (this.mdpForm.nouveau.length < 8) { this.mdpError = 'Minimum 8 caractères.'; return; }
    if (this.mdpForm.nouveau !== this.mdpForm.confirmation) { this.mdpError = 'Les mots de passe ne correspondent pas.'; return; }
    this.mdpLoading = true;
    this.auth.changerMotDePasse(this.mdpForm.ancien, this.mdpForm.nouveau, this.mdpForm.confirmation).subscribe({
      next: () => { this.mdpLoading = false; this.showMdpModal = false; this.showToast('Mot de passe modifié ✓', 'success'); },
      error: (err) => { this.mdpLoading = false; this.mdpError = err.error?.error || 'Erreur'; }
    });
  }
  

  goBack(): void {
    const isAdmin = this.currentUser?.role === 'admin';
    this.router.navigate([isAdmin ? '/admin' : '/triage']);
  }

  async showToast(message: string, color: string): Promise<void> {
    const t = await this.toastCtrl.create({ message, color, duration: 2500, position: 'bottom' });
    await t.present();
  }
  // ═══════════════════════════════════════════
  // MON PLANNING
  // ═══════════════════════════════════════════

  loadMonPlanning(): void {
    this.planningLoading = true;
    this.auth.getMonPlanning().subscribe({
      next: (data) => { this.monPlanning = data; this.planningLoading = false; },
      error: () => { this.planningLoading = false; }
    });
  }

  getPlanningJour(jourIndex: number): any[] {
    const d = this.getDateSemaine(jourIndex);
    return this.monPlanning.filter(p => p.date === d);
  }

  getDateSemaine(jourIndex: number): string {
    const today = new Date();
    const lundi = new Date(today);
    lundi.setDate(today.getDate() - today.getDay() + 1);
    const jour = new Date(lundi);
    jour.setDate(lundi.getDate() + jourIndex);
    return jour.toISOString().split('T')[0];
  }

  isAujourdhui(jourIndex: number): boolean {
    return this.getDateSemaine(jourIndex) === new Date().toISOString().split('T')[0];
  }

  creneauLabel(creneau: string): string {
    return { 'matin': '7h-13h', 'aprem': '13h-19h', 'nuit': '19h-7h' }[creneau] || creneau;
  }

  creneauIcon(creneau: string): string {
    return { 'matin': 'sunny', 'aprem': 'partly-sunny', 'nuit': 'moon' }[creneau] || 'time';
  }
  

  logout(): void { this.auth.logout(); }
}