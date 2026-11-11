import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { IonicModule, AlertController, ToastController } from '@ionic/angular';
import { debounceTime, from, Subject } from 'rxjs';
import { AuthService, Infirmier } from '../../services/auth.service';
import { InfirmiersService, StatistiquesAdmin } from '../../services/infirmiers.service';
import { AdminDashboardService,DashboardData, Alerte, Lit, Equipement} 
from '../../services/admin-dashboard.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.page.html',
  styleUrls: ['./admin.page.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, IonicModule],
})
export class AdminPage implements OnInit, OnDestroy {

  // ── Onglet principal ──────────────────────
  activeTab: 'comptes' | 'dashboard' | 'ressources' | 'remarques' = 'comptes';
  // ── Comptes (existant) ────────────────────
  infirmiers: Infirmier[] = [];
  stats: StatistiquesAdmin | null = null;
  loading = false;
  currentUser: Infirmier | null = null;

  searchTerm = '';
  filtreRole = '';
  filtreStatut = '';
  private searchSubject = new Subject<void>();

  showModal = false;
  editingUser: Infirmier | null = null;
  userForm!: FormGroup;
  modalLoading = false;
  modalError = '';

  showResetModal = false;
  resetTargetUser: Infirmier | null = null;
  newPassword = '';

  showQrModal = false;
  newlyCreatedUser: any = null;
  newlyCreatedQr = '';

  private colors = ['#09637E','#088395','#0a7a8a','#0d6b7a','#0b5c6e','#0e8a9c'];

  // ── Dashboard  ──────────────────
  dashData: DashboardData | null = null;
  dashLoading = true;
  // ── Panneau alertes latéral ───────────────
  alertePanelOpen = false;
  alerteBubbleOnly = true; // commence en mode bulle
  alerteExpandedId: string | null = null;

  get alerteMaxSeverite(): string {
    if (!this.dashData || !this.dashData.alertes.length) return 'none';
    if (this.dashData.alertes.some(a => a.severite === 'critique')) return 'critique';
    if (this.dashData.alertes.some(a => a.severite === 'avertissement')) return 'avertissement';
    return 'info';
  }

  get alerteCount(): number {
    return this.dashData?.alertes?.length || 0;
  }

  toggleAlertePanel(): void {
    this.alertePanelOpen = !this.alertePanelOpen;
    this.alerteBubbleOnly = !this.alertePanelOpen;
  }

  fermerAlertePanel(): void {
    this.alertePanelOpen = false;
    this.alerteBubbleOnly = true;
  }
  toggleAlerteDetail(id: string): void {
    this.alerteExpandedId = this.alerteExpandedId === id ? null : id;
  }

  getAlertesGroupees(): { type: string; label: string; icon: string; alertes: any[] }[] {
    if (!this.dashData) return [];

    const groupes: Record<string, { label: string; icon: string; alertes: any[] }> = {
      'personnel':   { label: 'Personnel',    icon: 'people-outline',          alertes: [] },
      'lits':        { label: 'Lits',          icon: 'bed-outline',             alertes: [] },
      'equipement':  { label: 'Équipements',   icon: 'hardware-chip-outline',   alertes: [] },
      'depassement': { label: 'Dépassements',  icon: 'timer-outline',           alertes: [] },
      'flux':        { label: 'Flux patients',  icon: 'trending-up-outline',     alertes: [] },
    };

    this.dashData.alertes.forEach((a, i) => {
      const alerte = { ...a, _index: i };
      if (groupes[a.type]) {
        groupes[a.type].alertes.push(alerte);
      }
    });

    return Object.entries(groupes)
      .filter(([, g]) => g.alertes.length > 0)
      .map(([type, g]) => ({ type, ...g }));
  }

  maxSeveriteGroupe(alertes: any[]): string {
    if (alertes.some(a => a.severite === 'critique')) return 'critique';
    if (alertes.some(a => a.severite === 'avertissement')) return 'avertissement';
    return 'info';
  }
  goToProfil(): void {
    this.router.navigate(['/profil']);
  }

  // ── Ressources ─────────────────
  activeRessource: 'lits' | 'equipements' | 'personnel' = 'lits';

  litsDetails: Lit[] = [];
  litsLoading = false;

  equipLoading = false;
  showEquipModal = false;
  editingEquip: Equipement | null = null;
  equipForm = { nom: '', total: 0, disponible: 0, seuil_alerte: 0, unite: 'appareils' };
  equipModalLoading = false;

  showLitModal = false;
  litForm = { numero: '', type: 'urgence', categorie: 'P2-P3' };

  personnelList: Infirmier[] = [];
  personnelLoading = false;

  alertes: Alerte[] = [];
  alertesLoading = false;
  // Remarques
  remarques: any[] = [];
  remarquesLoading = false;
  showReponseModal = false;
  remarqueTarget: any = null;
  reponseText = '';
  reponseLoading = false;
  // Planning
  planningData: any[] = [];
  planningLoading = false;
  planningInfirmiers: Infirmier[] = [];
  semaineDates: { date: string; label: string; jour: string }[] = [];
  semaineOffset = 0;
  // Statistiques avancées
  statsAvancees: any = null;
  statsLoading = false;
  historique: any[] = [];
  historiqueLoading = false;
  historiqueDate: string = new Date().toISOString().split('T')[0];
  historiqueDateLabel: string = '';
  // Export PDF
  showExportModal = false;
  exportMois = '';
  exportLoading = false;
  exportData: any = null;

  private refreshInterval: any;

  constructor(
    private auth: AuthService,
    private infirmiersService: InfirmiersService,
    private dashService: AdminDashboardService,
    private fb: FormBuilder,
    private alertCtrl: AlertController,
    private toastCtrl: ToastController,
    private router: Router
    
  ) {
    this.searchSubject.pipe(debounceTime(300)).subscribe(() => this.loadInfirmiers());
  }

  ngOnInit(): void {
    this.currentUser = this.auth.currentUser$.value;
    this.loadAll();
    this.loadDashboard();
    this.refreshInterval = setInterval(() => this.loadDashboard(true), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
  }

  // ── Changement d'onglet ───────────────────
  onTabChange(tab: string): void {
    this.activeTab = tab as any;
    if (tab === 'dashboard') {
      this.loadDashboard();
      this.loadStatsAvancees();
      this.loadHistorique();
    }
    if (tab === 'ressources') this.onRessourceChange(this.activeRessource);
    if (tab === 'remarques') this.loadRemarques();
  }

  // ═══════════════════════════════════════════
  // COMPTES (code existant inchangé)
  // ═══════════════════════════════════════════

  loadAll(): void { this.loadInfirmiers(); this.loadStats(); }

  loadInfirmiers(): void {
    this.loading = true;
    this.infirmiersService.getAll({
      role: this.filtreRole || undefined,
      statut: this.filtreStatut || undefined,
      search: this.searchTerm || undefined,
    }).subscribe({
      next: (data) => { this.infirmiers = data; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  loadStats(): void {
    this.infirmiersService.getStatistiques().subscribe(s => this.stats = s);
  }

  onSearch(): void { this.searchSubject.next(); }
  clearSearch(): void { this.searchTerm = ''; this.loadInfirmiers(); }
  applyFiltres(): void { this.loadInfirmiers(); }
  getAvatarColor(nom: string): string {
    return this.colors[(nom?.charCodeAt(0) || 0) % this.colors.length];
  }

  openCreateModal(): void {
    this.editingUser = null;
    this.userForm = this.fb.group({
      prenom: ['', Validators.required],
      nom: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      role: ['infirmier', Validators.required],
      service: [''],
      telephone: [''],
    });
    this.modalError = '';
    this.showModal = true;
  }

  openEditModal(user: Infirmier): void {
    this.editingUser = user;
    this.userForm = this.fb.group({
      prenom: [user.prenom, Validators.required],
      nom: [user.nom, Validators.required],
      email: [user.email, [Validators.required, Validators.email]],
      role: [user.role, Validators.required],
      service: [user.service || ''],
      telephone: [user.telephone || ''],
    });
    this.modalError = '';
    this.showModal = true;
  }

  closeModal(): void { this.showModal = false; this.editingUser = null; }

  saveUser(): void {
    if (this.userForm.invalid) { this.userForm.markAllAsTouched(); return; }
    this.modalLoading = true;
    this.modalError = '';
    const call = this.editingUser
      ? this.infirmiersService.update(this.editingUser.id, this.userForm.value)
      : this.infirmiersService.create(this.userForm.value);
    call.subscribe({
      next: (res: any) => {
        this.modalLoading = false;
        this.closeModal();
        this.loadAll();
        if (!this.editingUser && res.qr_code_base64) {
          this.newlyCreatedUser = res;
          this.newlyCreatedQr = res.qr_code_base64;
          this.showQrModal = true;
        } else {
          this.showToast(this.editingUser ? 'Compte modifié ✓' : 'Compte créé ✓', 'success');
        }
      },
      error: (err: any) => {
        this.modalLoading = false;
        this.modalError = err.error?.error || 'Une erreur est survenue.';
      }
    });
  }

  closeQrModal(): void { this.showQrModal = false; this.newlyCreatedQr = ''; }

  async toggleStatut(user: Infirmier): Promise<void> {
    const nouveau = user.statut === 'actif' ? 'inactif' : 'actif';
    const alert = await this.alertCtrl.create({
      header: 'Confirmation',
      message: `${nouveau === 'actif' ? 'Activer' : 'Désactiver'} le compte de ${user.nom_complet} ?`,
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Confirmer', handler: () => {
          this.infirmiersService.toggleStatut(user.id, nouveau).subscribe({
            next: () => { this.loadAll(); this.showToast('Statut mis à jour ✓', 'success'); },
            error: () => this.showToast('Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  openResetMdp(user: Infirmier): void {
    this.resetTargetUser = user;
    this.newPassword = '';
    this.modalError = '';
    this.showResetModal = true;
  }

  closeResetModal(): void { this.showResetModal = false; }

  saveResetMdp(): void {
    if (this.newPassword.length < 8) { this.modalError = 'Minimum 8 caractères.'; return; }
    this.modalLoading = true;
    this.infirmiersService.reinitialiserMdp(this.resetTargetUser!.id, this.newPassword).subscribe({
      next: () => { this.modalLoading = false; this.closeResetModal(); this.showToast('MDP réinitialisé ✓', 'success'); },
      error: () => { this.modalLoading = false; this.modalError = 'Erreur.'; }
    });
  }

  async confirmDelete(user: Infirmier): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Supprimer le compte',
      message: `Supprimer définitivement ${user.nom_complet} ? Action irréversible.`,
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Supprimer', handler: () => {
          this.infirmiersService.delete(user.id).subscribe({
            next: () => { this.loadAll(); this.showToast('Compte supprimé', 'warning'); },
            error: () => this.showToast('Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  // ═══════════════════════════════════════════
  // DASHBOARD (Sprint 5)
  // ═══════════════════════════════════════════

  loadDashboard(silent = false): void {
    if (!silent) this.dashLoading = true;
    this.dashService.getDashboard().subscribe({
      next: (data) => { this.dashData = data; this.dashLoading = false; },
      error: () => { this.dashLoading = false; }
    });
  }

  loadAlertes(): void {
    this.alertesLoading = true;
    this.dashService.getAlertes(100).subscribe({
      next: (data) => { this.alertes = data.alertes; this.alertesLoading = false; },
      error: () => { this.alertesLoading = false; }
    });
  }

  marquerToutesLues(): void {
    this.dashService.marquerToutesLues().subscribe({
      next: () => {
        this.alertes.forEach(a => a.lue = true);
        this.loadDashboard(true);
        this.showToast('Alertes marquées comme lues', 'success');
      }
    });
  }

  // ═══════════════════════════════════════════
  // RESSOURCES (Sprint 5)
  // ═══════════════════════════════════════════

  onRessourceChange(section: string): void {
    this.activeRessource = section as any;
    if (section === 'lits') this.loadLitsDetails();
    if (section === 'equipements') this.loadDashboard(true);
    if (section === 'personnel') this.loadPlanning();
  }

  // ── Lits ──────────────────────────────────
  loadLitsDetails(): void {
    this.litsLoading = true;
    this.dashService.getLits().subscribe({
      next: (data) => { this.litsDetails = data; this.litsLoading = false; },
      error: () => { this.litsLoading = false; }
    });
  }

  openLitModal(): void {
    this.litForm = { numero: '', type: 'urgence', categorie: 'P2-P3' };
    this.showLitModal = true;
  }

  saveLit(): void {
    if (!this.litForm.numero) return;
    this.dashService.creerLit(this.litForm).subscribe({
      next: () => {
        this.showLitModal = false;
        this.loadLitsDetails();
        this.loadDashboard(true);
        this.showToast('Lit ajouté ✓', 'success');
      },
      error: () => this.showToast('Erreur', 'danger')
    });
  }

  async supprimerLit(lit: Lit): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Supprimer le lit',
      message: `Supprimer le lit ${lit.numero} ?`,
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Supprimer', handler: () => {
          this.dashService.supprimerLit(lit.id).subscribe({
            next: () => {
              this.loadLitsDetails();
              this.loadDashboard(true);
              this.showToast('Lit supprimé', 'warning');
            },
            error: (err: any) => this.showToast(err.error?.error || 'Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  onLitTypeChange(): void {
    const m: Record<string, string> = { 'reanimation': 'P1', 'urgence': 'P2-P3', 'observation': 'P4-P5' };
    this.litForm.categorie = m[this.litForm.type] || '';
  }

  // ── Équipements ───────────────────────────
  openEquipModal(eq?: Equipement): void {
    if (eq) {
      this.editingEquip = eq;
      this.equipForm = { nom: eq.nom, total: eq.total, disponible: eq.disponible, seuil_alerte: eq.seuil_alerte, unite: eq.unite };
    } else {
      this.editingEquip = null;
      this.equipForm = { nom: '', total: 0, disponible: 0, seuil_alerte: 0, unite: 'appareils' };
    }
    this.showEquipModal = true;
  }

  saveEquipement(): void {
    if (!this.equipForm.nom) return;
    this.equipModalLoading = true;
    const call = this.editingEquip
      ? this.dashService.updateEquipement(this.editingEquip.id, this.equipForm)
      : this.dashService.creerEquipement(this.equipForm);
    call.subscribe({
      next: () => {
        this.equipModalLoading = false;
        this.showEquipModal = false;
        this.loadDashboard(true);
        this.showToast(this.editingEquip ? 'Modifié ✓' : 'Ajouté ✓', 'success');
      },
      error: () => { this.equipModalLoading = false; this.showToast('Erreur', 'danger'); }
    });
  }

  async supprimerEquipement(eq: Equipement): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Supprimer',
      message: `Supprimer ${eq.nom} ?`,
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Supprimer', handler: () => {
          this.dashService.supprimerEquipement(eq.id).subscribe({
            next: () => { this.loadDashboard(true); this.showToast('Supprimé', 'warning'); },
            error: () => this.showToast('Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  // ── Personnel ─────────────────────────────
  loadPersonnel(): void {
    this.personnelLoading = true;
    this.infirmiersService.getAll({ statut: 'actif' }).subscribe({
      next: (data) => { this.personnelList = data; this.personnelLoading = false; },
      error: () => { this.personnelLoading = false; }
    });
  }

  toggleService(inf: Infirmier): void {
    const enService = !inf.en_service;
    this.dashService.toggleService(inf.id, enService).subscribe({
      next: (updated: any) => {
        const idx = this.personnelList.findIndex(i => i.id === inf.id);
        if (idx >= 0) this.personnelList[idx] = updated;
        this.loadDashboard(true);
        this.showToast(enService ? `${inf.nom_complet} en service ✓` : `${inf.nom_complet} hors service`, enService ? 'success' : 'warning');
      },
      error: () => this.showToast('Erreur', 'danger')
    });
  }

  // ═══════════════════════════════════════════
  // UTILITAIRES
  // ═══════════════════════════════════════════

  couleurUrgence(niveau: string): string {
    const c: Record<string, string> = { 'P1': '#c0392b', 'P2': '#e67e22', 'P3': '#f1c40f', 'P4': '#27ae60', 'P5': '#7AB2B2' };
    return c[niveau] || '#95a5a6';
  }

  couleurSeverite(sev: string): string {
    return { 'critique': '#c0392b', 'avertissement': '#e67e22', 'info': '#088395' }[sev] || '#95a5a6';
  }

  iconeSeverite(sev: string): string {
    return { 'critique': 'alert-circle', 'avertissement': 'warning', 'info': 'information-circle' }[sev] || 'help-circle';
  }

  pourcentage(dispo: number, total: number): number {
    return total > 0 ? Math.round((dispo / total) * 100) : 0;
  }

  niveauxKeys(): string[] { return ['P1', 'P2', 'P3', 'P4', 'P5']; }

  async showToast(message: string, color: string): Promise<void> {
    const toast = await this.toastCtrl.create({ message, color, duration: 2500, position: 'bottom' });
    await toast.present();
  }
  imprimerBadge(inf: Infirmier): void {
    if (!inf.qr_code_base64) {
      this.showToast('QR code non disponible pour cet infirmier', 'warning');
      return;
    }

    const roleLabel = inf.role === 'admin' ? 'Administrateur' : 'Infirmier(ère)';
    const service = inf.service || 'Non assigné';

    const printWindow = window.open('', '_blank', 'width=400,height=600');
    if (!printWindow) {
      this.showToast('Popup bloquée — autorisez les popups', 'danger');
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html lang="fr">
      <head>
        <meta charset="UTF-8"/>
        <title>Badge — ${inf.nom_complet}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; background: #f0f0f0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          }
          .badge {
            width: 320px; background: white; border-radius: 16px;
            overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
          }
          .badge-header {
            background: linear-gradient(135deg, #09637E, #088395);
            padding: 20px; text-align: center; color: white;
          }
          .badge-logo { font-size: 28px; margin-bottom: 4px; }
          .badge-app-name {
            font-size: 20px; font-weight: 800;
            letter-spacing: -0.5px; margin-bottom: 2px;
          }
          .badge-subtitle {
            font-size: 11px; opacity: 0.8;
          }
          .badge-body { padding: 24px; text-align: center; }
          .badge-avatar {
            width: 56px; height: 56px; border-radius: 50%;
            background: #09637E; color: white;
            font-size: 20px; font-weight: 700;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 12px;
          }
          .badge-name {
            font-size: 18px; font-weight: 700; color: #0d2e38;
            margin-bottom: 4px;
          }
          .badge-role {
            display: inline-block;
            background: #EBF4F6; color: #09637E;
            padding: 3px 12px; border-radius: 6px;
            font-size: 12px; font-weight: 600;
            margin-bottom: 4px;
          }
          .badge-service {
            font-size: 12px; color: #5a8a96;
            margin-bottom: 16px;
          }
          .badge-qr {
            padding: 12px; background: #f8fbfc;
            border: 2px dashed #c5dde3; border-radius: 12px;
            display: inline-block; margin-bottom: 12px;
          }
          .badge-qr img {
            width: 160px; height: 160px; border-radius: 8px;
          }
          .badge-scan-hint {
            font-size: 11px; color: #7AB2B2;
            margin-bottom: 0;
          }
          .badge-footer {
            background: #09637E; padding: 10px;
            text-align: center;
          }
          .badge-footer p {
            color: rgba(255,255,255,0.7); font-size: 10px;
          }
          @media print {
            body { background: white; min-height: auto; }
            .badge { box-shadow: none; border: 1px solid #ddd; }
          }
        </style>
      </head>
      <body>
        <div class="badge">
          <div class="badge-header">
            <div class="badge-logo">🏥</div>
            <div class="badge-app-name">TriagePro</div>
            <div class="badge-subtitle">Système de triage médical</div>
          </div>
          <div class="badge-body">
            <div class="badge-avatar">
              ${inf.prenom?.charAt(0) || ''}${inf.nom?.charAt(0) || ''}
            </div>
            <div class="badge-name">${inf.nom_complet}</div>
            <div class="badge-role">${roleLabel}</div>
            <div class="badge-service">Service : ${service}</div>
            <div class="badge-qr">
              <img src="data:image/png;base64,${inf.qr_code_base64}" alt="QR Code"/>
            </div>
            <p class="badge-scan-hint">Scannez pour connexion rapide</p>
          </div>
          <div class="badge-footer">
            <p>© 2026 TriagePro · Badge de connexion personnel</p>
          </div>
        </div>

        <script>
          window.onload = function() {
            setTimeout(function() { window.print(); }, 300);
          };
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
  }
  // ── Remarques infirmiers ──────────────────
  loadRemarques(): void {
    this.remarquesLoading = true;
    this.dashService.getRemarques().subscribe({
      next: (data) => { this.remarques = data; this.remarquesLoading = false; },
      error: () => { this.remarquesLoading = false; }
    });
  }

  openReponseModal(remarque: any): void {
    this.remarqueTarget = remarque;
    this.reponseText = remarque.reponse || '';
    this.showReponseModal = true;
  }

  envoyerReponse(): void {
    if (!this.reponseText.trim()) return;
    this.reponseLoading = true;
    this.dashService.repondreRemarque(this.remarqueTarget.id, this.reponseText).subscribe({
      next: () => {
        this.reponseLoading = false;
        this.showReponseModal = false;
        this.loadRemarques();
        this.showToast('Réponse envoyée ✓', 'success');
      },
      error: () => { this.reponseLoading = false; this.showToast('Erreur', 'danger'); }
    });
  }
  get hasRemarquesNonRepondues(): boolean {
    return this.remarques.length > 0 && this.remarques.some(r => !r.reponse);
  }

  // ═══════════════════════════════════════════
  // PLANNING
  // ═══════════════════════════════════════════

  loadPlanning(): void {
    this.planningLoading = true;
    this.calculerSemaine();

    const lundi = this.semaineDates[0]?.date;

    // Charger infirmiers actifs
    this.infirmiersService.getAll({ statut: 'actif' }).subscribe({
      next: (data) => { this.planningInfirmiers = data; }
    });

    // Charger planning
    this.dashService.getPlanning(lundi).subscribe({
      next: (data) => { this.planningData = data; this.planningLoading = false; },
      error: () => { this.planningLoading = false; }
    });
  }

  calculerSemaine(): void {
    const today = new Date();
    today.setDate(today.getDate() + (this.semaineOffset * 7));
    const lundi = new Date(today);
    lundi.setDate(today.getDate() - today.getDay() + 1);

    const jours = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
    this.semaineDates = [];

    for (let i = 0; i < 7; i++) {
      const d = new Date(lundi);
      d.setDate(lundi.getDate() + i);
      const dateStr = d.toISOString().split('T')[0];
      const label = `${d.getDate()}/${d.getMonth() + 1}`;
      this.semaineDates.push({ date: dateStr, label, jour: jours[i] });
    }
  }

  semainePrecedente(): void {
    this.semaineOffset--;
    this.loadPlanning();
  }

  semaineSuivante(): void {
    this.semaineOffset++;
    this.loadPlanning();
  }

  semaineActuelle(): void {
    this.semaineOffset = 0;
    this.loadPlanning();
  }

  isPlanned(infirmierId: string, date: string, creneau: string): boolean {
    return this.planningData.some(
      p => p.infirmier_id === infirmierId && p.date === date && p.creneau === creneau
    );
  }

  togglePlanningCell(infirmierId: string, date: string, creneau: string): void {
    this.dashService.togglePlanning(infirmierId, date, creneau).subscribe({
      next: (res) => {
        if (res.action === 'added') {
          const inf = this.planningInfirmiers.find(i => i.id === infirmierId);
          this.planningData.push({
            infirmier_id: infirmierId,
            infirmier_nom: inf?.nom_complet || '',
            date, creneau
          });
        } else {
          this.planningData = this.planningData.filter(
            p => !(p.infirmier_id === infirmierId && p.date === date && p.creneau === creneau)
          );
        }
      },
      error: () => this.showToast('Erreur', 'danger')
    });
  }

  isToday(date: string): boolean {
    return date === new Date().toISOString().split('T')[0];
  }

  getSemaineLabel(): string {
    if (this.semaineDates.length === 0) return '';
    return `${this.semaineDates[0].label} — ${this.semaineDates[6].label}`;
  }

  countPlanningJour(date: string): number {
    return this.planningData.filter(p => p.date === date).length;
  }
  marquerRemarqueLue(remarque: any): void {
    this.dashService.marquerRemarqueLue(remarque.id).subscribe({
      next: () => {
        this.remarques = this.remarques.filter(r => r.id !== remarque.id);
        this.showToast('Remarque traitée ✓', 'success');
      },
      error: () => this.showToast('Erreur', 'danger')
    });
  }
  // ═══════════════════════════════════════════
  // STATISTIQUES AVANCÉES
  // ═══════════════════════════════════════════

  loadStatsAvancees(): void {
    this.statsLoading = true;
    this.dashService.getStatistiquesAvancees().subscribe({
      next: (data) => { this.statsAvancees = data; this.statsLoading = false; },
      error: () => { this.statsLoading = false; }
    });
  }
  loadHistorique(): void {
    this.historiqueLoading = true;
    this.updateHistoriqueDateLabel();
    this.dashService.getHistorique(100).subscribe({
      next: (data) => {
        // Filtrer par date sélectionnée
        this.historique = data.filter(p => {
          if (!p.date_creation) return false;
          const pDate = p.date_creation.split('T')[0];
          return pDate === this.historiqueDate;
        });
        this.historiqueLoading = false;
      },
      error: () => { this.historiqueLoading = false; }
    });
  }

  updateHistoriqueDateLabel(): void {
    const d = new Date(this.historiqueDate);
    const jours = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
    const mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'];
    this.historiqueDateLabel = `${jours[d.getDay()]} ${d.getDate()} ${mois[d.getMonth()]} ${d.getFullYear()}`;
  }

  historiqueJourPrecedent(): void {
    const d = new Date(this.historiqueDate);
    d.setDate(d.getDate() - 1);
    this.historiqueDate = d.toISOString().split('T')[0];
    this.loadHistorique();
  }

  historiqueJourSuivant(): void {
    const d = new Date(this.historiqueDate);
    d.setDate(d.getDate() + 1);
    this.historiqueDate = d.toISOString().split('T')[0];
    this.loadHistorique();
  }

  historiqueAujourdhui(): void {
    this.historiqueDate = new Date().toISOString().split('T')[0];
    this.loadHistorique();
  }

  isHistoriqueToday(): boolean {
    return this.historiqueDate === new Date().toISOString().split('T')[0];
  }

  tempsAttenteNiveaux(): string[] {
    return ['P1', 'P2', 'P3', 'P4', 'P5'];
  }

  getTempsAttente(niveau: string): string {
    if (!this.statsAvancees?.temps_attente_par_niveau?.[niveau]) return '—';
    const min = this.statsAvancees.temps_attente_par_niveau[niveau].moyenne_minutes;
    if (min < 60) return `${min} min`;
    const h = Math.floor(min / 60);
    const m = Math.round(min % 60);
    return `${h}h${m < 10 ? '0' + m : m}`;
  }

  getTempsAttenteCount(niveau: string): number {
    return this.statsAvancees?.temps_attente_par_niveau?.[niveau]?.count || 0;
  }

  getMaxAffluence(): number {
    if (!this.statsAvancees?.affluence_24h) return 1;
    return Math.max(1, ...this.statsAvancees.affluence_24h.map((a: any) => a.count));
  }

  barHeight(count: number): string {
    const max = this.getMaxAffluence();
    return Math.max(4, (count / max) * 100) + '%';
  }
  get remarquesNonTraitees(): any[] {
    return this.remarques.filter(r => !r.lue);
  }

  get remarquesTraitees(): any[] {
    return this.remarques.filter(r => r.lue);
  }
  // ═══════════════════════════════════════════
  // EXPORT PDF MENSUEL
  // ═══════════════════════════════════════════

  openExportModal(): void {
    const now = new Date();
    this.exportMois = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    this.exportData = null;
    this.showExportModal = true;
  }

  genererExportPDF(): void {
    this.exportLoading = true;
    this.dashService.getExportHistorique(this.exportMois).subscribe({
      next: (data) => {
        this.exportData = data;
        this.exportLoading = false;
        this.ouvrirPDF(data);
      },
      error: () => {
        this.exportLoading = false;
        this.showToast('Erreur de génération', 'danger');
      }
    });
  }

  ouvrirPDF(data: any): void {
    const maxAffluence = Math.max(1, ...data.affluence_jours.map((a: any) => a.count));

    const barsSVG = data.affluence_jours.map((a: any) => {
      const h = Math.max(3, (a.count / maxAffluence) * 120);
      const x = (a.jour - 1) * 22 + 40;
      return `
        <rect x="${x}" y="${140 - h}" width="16" height="${h}" rx="2" fill="#088395"/>
        <text x="${x + 8}" y="${155}" text-anchor="middle" font-size="7" fill="#666">${a.jour}</text>
        ${a.count > 0 ? `<text x="${x + 8}" y="${135 - h}" text-anchor="middle" font-size="7" fill="#333" font-weight="600">${a.count}</text>` : ''}
      `;
    }).join('');

    const niveaux = ['P1', 'P2', 'P3', 'P4', 'P5'];
    const couleurs: Record<string, string> = { P1: '#c0392b', P2: '#e67e22', P3: '#f1c40f', P4: '#27ae60', P5: '#2980b9' };

    const distRows = niveaux.map(n => `
      <tr>
        <td style="text-align:center"><span style="background:${couleurs[n]};color:white;padding:2px 10px;border-radius:4px;font-weight:700;font-size:11px">${n}</span></td>
        <td style="text-align:center;font-weight:600">${data.distribution[n] || 0}</td>
        <td style="text-align:center;color:#666">${data.temps_attente[n] ? data.temps_attente[n] + ' min' : '—'}</td>
      </tr>
    `).join('');

    const patientRows = data.patients.map((p: any, i: number) => `
      <tr style="background:${i % 2 === 0 ? 'white' : '#f8fbfc'}">
        <td style="font-weight:600">${p.prenom} ${p.nom}</td>
        <td style="text-align:center">${p.age} ans</td>
        <td style="text-align:center">${p.sexe}</td>
        <td style="text-align:center"><span style="background:${couleurs['P' + p.degre_urgence] || '#999'};color:white;padding:1px 8px;border-radius:4px;font-size:10px;font-weight:700">P${p.degre_urgence}</span></td>
        <td>${p.infirmier_nom}</td>
        <td style="text-align:center">${p.lit_numero || '—'}</td>
        <td style="text-align:center;color:#666;font-size:11px">${p.date_creation}</td>
      </tr>
    `).join('');

    const printWindow = window.open('', '_blank', 'width=900,height=700');
    if (!printWindow) { this.showToast('Popup bloquée', 'danger'); return; }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html lang="fr">
      <head>
        <meta charset="UTF-8"/>
        <title>Rapport mensuel — ${data.mois_label}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; color: #0d2e38; }
          
          .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 3px solid #09637E; }
          .header h1 { font-size: 22px; color: #09637E; }
          .header .subtitle { font-size: 13px; color: #5a8a96; }
          .header .logo { font-size: 28px; font-weight: 800; color: #09637E; }

          .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 25px; }
          .stat-box { background: #EBF4F6; border-radius: 10px; padding: 15px; text-align: center; }
          .stat-value { font-size: 28px; font-weight: 800; color: #09637E; }
          .stat-label { font-size: 11px; color: #5a8a96; margin-top: 4px; }

          .section-title { font-size: 15px; font-weight: 700; color: #09637E; margin: 20px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #c5dde3; }

          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }
          th { background: #09637E; color: white; padding: 8px 10px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
          td { padding: 7px 10px; border-bottom: 1px solid #eef2f3; }

          .chart-wrap { background: #f8fbfc; border-radius: 10px; padding: 20px; margin-bottom: 20px; }

          .footer { margin-top: 30px; padding-top: 12px; border-top: 2px solid #09637E; display: flex; justify-content: space-between; font-size: 10px; color: #5a8a96; }

          @media print {
            body { padding: 15px; }
            .stats-grid { break-inside: avoid; }
            table { break-inside: auto; }
            tr { break-inside: avoid; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <h1>Rapport mensuel des triages</h1>
            <div class="subtitle">${data.mois_label} — Service des urgences</div>
          </div>
          <div class="logo">TriagePro</div>
        </div>

        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-value">${data.total_patients}</div>
            <div class="stat-label">Patients triés</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">${data.total_evalues}</div>
            <div class="stat-label">Évaluations IA</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">${data.taux_correction}%</div>
            <div class="stat-label">Corrections manuelles</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">${data.total_corriges}</div>
            <div class="stat-label">Corrigés sur ${data.total_evalues}</div>
          </div>
        </div>

        <div class="section-title">Distribution par niveau de priorité</div>
        <table>
          <thead><tr><th>Niveau</th><th style="text-align:center">Patients</th><th style="text-align:center">Temps attente moyen</th></tr></thead>
          <tbody>${distRows}</tbody>
        </table>

        <div class="section-title">Affluence journalière — ${data.mois_label}</div>
        <div class="chart-wrap">
          <svg width="100%" viewBox="0 0 ${data.affluence_jours.length * 22 + 60} 170" xmlns="http://www.w3.org/2000/svg">
            <line x1="35" y1="140" x2="${data.affluence_jours.length * 22 + 45}" y2="140" stroke="#c5dde3" stroke-width="0.5"/>
            ${barsSVG}
          </svg>
        </div>

        <div class="section-title">Liste complète des triages (${data.total_patients} patients)</div>
        <table>
          <thead>
            <tr>
              <th>Patient</th><th style="text-align:center">Âge</th><th style="text-align:center">Sexe</th>
              <th style="text-align:center">Niveau</th><th>Infirmier</th><th style="text-align:center">Lit</th>
              <th style="text-align:center">Date / Heure</th>
            </tr>
          </thead>
          <tbody>${patientRows}</tbody>
        </table>

        <div class="footer">
          <span>TriagePro — Système intelligent d'aide au triage médical</span>
          <span>Généré le ${new Date().toLocaleDateString('fr-FR')} à ${new Date().toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}</span>
        </div>

        <script>
          window.onload = function() { setTimeout(function() { window.print(); }, 500); };
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
    this.showExportModal = false;
  }

  logout(): void { this.auth.logout(); }
}