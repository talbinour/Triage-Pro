import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, ToastController, AlertController, AlertInput } from '@ionic/angular';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { TriageService, Patient, PredictionResult } from '../../services/triage.service';
import { Router } from '@angular/router';
@Component({
  selector: 'app-triage',
  templateUrl: './triage.page.html',
  styleUrls: ['./triage.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, ReactiveFormsModule],
})
export class TriagePage implements OnInit , OnDestroy {

  activeTab: 'formulaire' | 'attente' | 'consultation' = 'formulaire';  currentUser = this.auth.currentUser$.value;
  patientForm: FormGroup;
  loading = false;

  // Listes patients séparées
  patientsAttente: Patient[] = [];
  patientsConsultation: Patient[] = [];
  loadingListe = false;

  // Modal résultat IA
  predictionIA: PredictionResult | null = null;
  loadingIA = false;
  showModal = false;
  niveauManuel: number | null = null;
  modificationManuelle = false;

  // Modal prise en charge (choix du lit)
  showLitModal = false;
  litsLibres: any[] = [];
  litsLoading = false;
  patientAPrendre: Patient | null = null;
  // Countdown timer
  private countdownInterval: any;
  filtreDepassement = false;
  // Timer rafraîchissement
  private timerInterval: any;

  iotConnected   = false;
  iotLoading     = false;
  iotImported    = false;
  iotImportedFields = 0;
  iotLastUpdate  = '';

  constructor(
    private auth: AuthService,
    private fb: FormBuilder,
    private triageService: TriageService,
    private toastCtrl: ToastController,
    private alertCtrl: AlertController,
    private router: Router
  ) {
    this.patientForm = this.fb.group({
      nom:          ['', Validators.required],
      prenom:       ['', Validators.required],
      age:          ['', [Validators.required, Validators.min(0), Validators.max(120)]],
      sexe:         ['', Validators.required],
      temperature:  ['', [Validators.required, Validators.min(30), Validators.max(45)]],
      oxygene:      ['', [Validators.required, Validators.min(50), Validators.max(100)]],
      pouls:        ['', [Validators.required, Validators.min(20), Validators.max(300)]],
      sbp:          ['', [Validators.required, Validators.min(40), Validators.max(300)]],
      dbp:          ['', [Validators.required, Validators.min(20), Validators.max(200)]],
      rr:           ['', [Validators.required, Validators.min(5),  Validators.max(60)]],
      mental:       ['1', Validators.required],
      pain:         ['0', Validators.required],
      nrs_pain:     ['0'],
      arrival_mode: ['3', Validators.required],
      injury:       ['1', Validators.required],
      symptome1:    [''],
      symptome2:    [''],
    });
  }
  ngOnDestroy(): void {
    if (this.countdownInterval) clearInterval(this.countdownInterval);
  }

  ngOnInit(): void {
    this.chargerPatients();
    
    this.countdownInterval = setInterval(() => {
      
      this.patientsAttente = [...this.patientsAttente];
    }, 1000);
  }

  chargerPatients(): void {
    this.loadingListe = true;
    this.triageService.getTousPatients().subscribe({
      next: (data) => {
        this.patientsAttente = data.filter(p => p.statut === 'en_attente');
        this.patientsConsultation = data.filter(p => p.statut === 'en_consultation');
        this.loadingListe = false;
      },
      error: () => { this.loadingListe = false; }
    });
  }

  allerVersListe(): void {
    this.activeTab = 'attente';
    this.chargerPatients();
  }

  isInvalid(field: string): boolean {
    const c = this.patientForm.get(field);
    return !!(c?.invalid && c?.touched);
  }
  goToProfil(): void {
    this.router.navigate(['/profil']);
  }

  // ═══════════════════════════════════════════
  // SOUMISSION → IA → MODAL
  // ═══════════════════════════════════════════

  onSubmit(): void {
    if (this.patientForm.invalid) {
      this.patientForm.markAllAsTouched();
      return;
    }
    const formVal = this.patientForm.value;
    const sexeInt = formVal.sexe === 'M' ? 2 : 1;
    const dataIA = {
      age: Number(formVal.age), sexe: sexeInt,
      temperature: Number(formVal.temperature),
      spo2: Number(formVal.oxygene), pouls: Number(formVal.pouls),
      sbp: Number(formVal.sbp), dbp: Number(formVal.dbp),
      rr: Number(formVal.rr), mental: Number(formVal.mental),
      pain: Number(formVal.pain), nrs_pain: Number(formVal.nrs_pain),
      arrival_mode: Number(formVal.arrival_mode),
      injury: Number(formVal.injury),
    };
    this.loadingIA = true;
    this.predictionIA = null;
    this.triageService.predictTriage(dataIA).subscribe({
      next: (result) => {
        this.predictionIA = result;
        this.loadingIA = false;
        this.showModal = true;
      },
      error: () => {
        this.loadingIA = false;
        this.showToast('Erreur IA — enregistrement sans évaluation', 'warning');
        this.enregistrerPatient(null);
      }
    });
  }

  fermerModal(): void {
    this.showModal = false;
    this.predictionIA = null;
    this.niveauManuel = null;
    this.modificationManuelle = false;
  }

  confirmerEtEnregistrer(): void {
    const niveau = this.niveauManuel
      ? this.niveauManuel
      : this.predictionIA
        ? parseInt(this.predictionIA.niveau.replace('P', ''))
        : null;
    this.showModal = false;
    this.niveauManuel = null;
    this.modificationManuelle = false;
    this.enregistrerPatient(niveau);
  }

  enregistrerPatient(niveau: number | null): void {
    this.loading = true;
    const formVal = this.patientForm.value;
    const patientData = { ...formVal, degre_urgence: niveau };
    this.triageService.creerPatient(patientData).subscribe({
      next: () => {
        this.loading = false;
        this.patientForm.reset();
        this.predictionIA = null;
        this.showToast('Patient enregistré ✓', 'success');
        this.allerVersListe();
      },
      error: (err) => {
        this.loading = false;
        this.showToast(err.error?.error || 'Erreur serveur', 'danger');
      }
    });
  }

  // ═══════════════════════════════════════════
  // PRISE EN CHARGE → CHOIX DU LIT
  // ═══════════════════════════════════════════

  ouvrirChoixLit(patient: Patient): void {
    this.patientAPrendre = patient;
    this.litsLoading = true;
    this.showLitModal = true;

    this.triageService.getLitsLibres().subscribe({
      next: (lits) => {
        if (lits.length === 0) {
          this.showLitModal = false;
          this.patientAPrendre = null;
          this.showAucunLitPopup();
          return;
        }

        let typeRecommande = 'observation';
        if (patient.degre_urgence === 1) typeRecommande = 'reanimation';
        else if (patient.degre_urgence && patient.degre_urgence <= 3) typeRecommande = 'urgence';

        this.litsLibres = lits.sort((a: any, b: any) => {
          if (a.type === typeRecommande && b.type !== typeRecommande) return -1;
          if (a.type !== typeRecommande && b.type === typeRecommande) return 1;
          return a.numero.localeCompare(b.numero);
        });
        this.litsLoading = false;
      },
      error: () => {
        this.litsLoading = false;
        this.showToast('Erreur chargement lits', 'danger');
      }
    });
  }

  async showAucunLitPopup(): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Aucun lit disponible',
      message: 'Tous les lits sont actuellement occupés. Veuillez terminer la consultation des patients en cours pour libérer des lits avant de prendre en charge un nouveau patient.',
      cssClass: 'alerte-aucun-lit',
      buttons: [
        {
          text: 'Voir les consultations',
          handler: () => {
            this.activeTab = 'consultation';
            this.chargerPatients();
          }
        },
        {
          text: 'Compris',
          role: 'cancel'
        }
      ]
    });
    await alert.present();
  }

  choisirLit(lit: any): void {
    if (!this.patientAPrendre) return;

    this.triageService.prendreEnCharge(
      this.patientAPrendre.id, lit.id
    ).subscribe({
      next: () => {
        this.showLitModal = false;
        this.patientAPrendre = null;
        this.chargerPatients();
        this.showToast(
          `Patient orienté vers le lit ${lit.numero} ✓`,
          'success'
        );
      },
      error: (err) => {
        this.showToast(
          err.error?.error || 'Erreur prise en charge',
          'danger'
        );
      }
    });
  }

  fermerLitModal(): void {
    this.showLitModal = false;
    this.patientAPrendre = null;
  }

  typeLitRecommande(patient: Patient): string {
    if (patient.degre_urgence === 1) return 'reanimation';
    if (patient.degre_urgence && patient.degre_urgence <= 3) return 'urgence';
    return 'observation';
  }

  // ═══════════════════════════════════════════
  // TERMINER CONSULTATION
  // ═══════════════════════════════════════════

  async terminerPatient(patient: Patient): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Terminer la consultation',
      message: `Confirmer la fin de consultation de ${patient.prenom} ${patient.nom} ?`
        + (patient.lit_numero ? `\nLe lit ${patient.lit_numero} sera libéré automatiquement.` : ''),
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Confirmer', handler: () => {
          this.triageService.terminerConsultation(patient.id).subscribe({
            next: () => {
              this.chargerPatients();
              this.showToast(
                `${patient.prenom} ${patient.nom} — consultation terminée ✓`
                + (patient.lit_numero ? ` · Lit ${patient.lit_numero} libéré` : ''),
                'success'
              );
            },
            error: () => this.showToast('Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  // ═══════════════════════════════════════════
  // MODIFICATION URGENCE (inchangé)
  // ═══════════════════════════════════════════

  async mettreAJourUrgence(patient: Patient): Promise<void> {
    const inputs: AlertInput[] = [1,2,3,4,5].map(n => ({
      type: 'radio' as const,
      label: `P${n} — ${this.labelUrgence(n).split('—')[1]?.trim()}`,
      value: n.toString(),
      checked: patient.degre_urgence === n
    }));
    const alert = await this.alertCtrl.create({
      header: 'Mettre à jour le niveau',
      message: `${patient.prenom} ${patient.nom}`,
      inputs,
      buttons: [
        { text: 'Annuler', role: 'cancel' },
        { text: 'Valider', handler: (value) => {
          this.triageService.updatePatient(patient.id, { degre_urgence: Number(value) }).subscribe({
            next: () => { this.chargerPatients(); this.showToast('Niveau mis à jour ✓', 'success'); },
            error: () => this.showToast('Erreur', 'danger')
          });
        }}
      ]
    });
    await alert.present();
  }

  // ═══════════════════════════════════════════
  // UTILITAIRES
  // ═══════════════════════════════════════════


  couleurUrgence(degre: number | null): string {
    const c: Record<number, string> = { 1: '#c0392b', 2: '#e67e22', 3: '#f1c40f', 4: '#27ae60', 5: '#7AB2B2' };
    return degre ? c[degre] : '#95a5a6';
  }

  labelUrgence(degre: number | null): string {
    const l: Record<number, string> = {
      1: 'P1 — Immédiat', 2: 'P2 — Très urgent',
      3: 'P3 — Urgent', 4: 'P4 — Peu urgent', 5: 'P5 — Non urgent'
    };
    return degre ? l[degre] : 'En attente';
  }

  probKeys(proba: { [key: string]: number }): string[] {
    return ['P1', 'P2', 'P3', 'P4', 'P5'].filter(k => k in proba);
  }

  async showToast(message: string, color: string) {
    const t = await this.toastCtrl.create({ message, color, duration: 2500, position: 'bottom' });
    await t.present();
  }

  onPainChange(): void {
    if (this.patientForm.get('pain')?.value === '0') {
      this.patientForm.patchValue({ nrs_pain: '0' });
    }
  }

  choisirNiveauManuel(niveau: number): void {
    this.niveauManuel = niveau;
    this.modificationManuelle = true;
  }

  ouvrirModification(): void {
    this.modificationManuelle = true;
  }
  // ═══════════════════════════════════════════
  // COUNTDOWN TIMER
  // ═══════════════════════════════════════════

  delaiMaxMinutes(degre: number | null): number {
    if (!degre) return 120;
    const d: Record<number, number> = {1: 2, 2: 10, 3: 30, 4: 60, 5: 120};
    return d[degre] || 120;
  }

  secondsRestantes(patient: Patient): number {
    if (!patient.date_creation || !patient.degre_urgence) return 0;
    const delaiMax = this.delaiMaxMinutes(patient.degre_urgence) * 60;
    const elapsed = (Date.now() - new Date(patient.date_creation).getTime()) / 1000;
    return Math.round(delaiMax - elapsed);
  }

  estEnDepassement(patient: Patient): boolean {
    return this.secondsRestantes(patient) < 0;
  }

  countdownDisplay(patient: Patient): string {
    const secs = this.secondsRestantes(patient);
    const absSecs = Math.abs(secs);
    const min = Math.floor(absSecs / 60);
    const sec = Math.floor(absSecs % 60);
    const pad = sec < 10 ? '0' + sec : sec;

    if (secs >= 0) {
      // Temps restant
      if (min >= 60) {
        const h = Math.floor(min / 60);
        const m = min % 60;
        return `${h}h${m < 10 ? '0' + m : m}:${pad}`;
      }
      return `${min}:${pad}`;
    } else {
      // Dépassement
      if (min >= 60) {
        const h = Math.floor(min / 60);
        const m = min % 60;
        return `+${h}h${m < 10 ? '0' + m : m}:${pad}`;
      }
      return `+${min}:${pad}`;
    }
  }

  countdownPourcent(patient: Patient): number {
    if (!patient.date_creation || !patient.degre_urgence) return 100;
    const delaiMax = this.delaiMaxMinutes(patient.degre_urgence) * 60;
    const elapsed = (Date.now() - new Date(patient.date_creation).getTime()) / 1000;
    const pct = Math.max(0, Math.min(100, ((delaiMax - elapsed) / delaiMax) * 100));
    return Math.round(pct);
  }

  countdownColor(patient: Patient): string {
    const pct = this.countdownPourcent(patient);
    if (pct <= 0) return '#c0392b';
    if (pct <= 25) return '#e67e22';
    if (pct <= 50) return '#f1c40f';
    return '#27ae60';
  }

  tempsAttente(date_creation: string): string {
    const diff = Date.now() - new Date(date_creation).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'À l\'instant';
    if (minutes < 60) return `${minutes} min`;
    const heures = Math.floor(minutes / 60);
    const reste = minutes % 60;
    return `${heures}h${reste < 10 ? '0' + reste : reste}`;
  }

  // Filtre patients en dépassement
  get patientsAffiches(): Patient[] {
    if (!this.filtreDepassement) return this.patientsAttente;
    return this.patientsAttente.filter(p => this.estEnDepassement(p));
  }

  toggleFiltreDepassement(): void {
    this.filtreDepassement = !this.filtreDepassement;
  }
 importerDepuisIoT(): void {
  this.iotLoading  = true;
  this.iotImported = false;

  this.triageService.getIoTVitals().subscribe({
    next: (data: any) => {
      let champsImportes = 0;
      const champs = ['temperature','oxygene','pouls','rr','sbp','dbp'];
      champs.forEach(champ => {
        if (data[champ] !== undefined && data[champ] !== null) {
          this.patientForm.get(champ)?.setValue(data[champ]);
          champsImportes++;
        }
      });
      this.iotConnected      = true;
      this.iotLoading        = false;
      this.iotImported       = true;
      this.iotImportedFields = champsImportes;
      this.iotLastUpdate     = new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    },
    error: (err: any) => {
      this.iotLoading   = false;
      this.iotConnected = false;
      this.iotImported  = false;
      this.showToast(
        err.status === 404
          ? 'Aucune donnée IoT — scannez d\'abord avec le bracelet'
          : 'Bracelet IoT non connecté',
        'danger'
      );
    }
  });
}
  logout(): void { this.auth.logout(); }
}