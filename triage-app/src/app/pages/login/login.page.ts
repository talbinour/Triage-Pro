import { Component, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth.service';
import { API_BASE } from '../../api.config';
import jsQR from 'jsqr';

@Component({
  selector: 'app-login',
  templateUrl: './login.page.html',
  styleUrls: ['./login.page.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, IonicModule],
})
export class LoginPage implements OnDestroy {
  @ViewChild('video') videoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  loginForm: FormGroup;
  loading = false;
  showPassword = false;
  serverError = '';
  activeTab: 'email' | 'qr' = 'email';
  scanning = false;
  manualToken = '';

  private stream: MediaStream | null = null;
  private animFrame: any;

  constructor(
    private fb: FormBuilder,
    private auth: AuthService,
    private router: Router,
    private http: HttpClient
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
    });
    if (this.auth.isAuthenticated()) this.redirectAfterLogin();

    const token = new URLSearchParams(window.location.search).get('token');
    if (token) this.loginWithQrToken(token);
  }

  isFieldInvalid(field: string): boolean {
    const c = this.loginForm.get(field);
    return !!(c?.invalid && c?.touched);
  }

  onLogin(): void {
    if (this.loginForm.invalid) { this.loginForm.markAllAsTouched(); return; }
    this.loading = true;
    this.serverError = '';
    const { email, password } = this.loginForm.value;
    this.auth.login(email, password).subscribe({
      next: () => { this.loading = false; this.redirectAfterLogin(); },
      error: (err) => {
        this.loading = false;
        this.serverError = err.error?.error || 'Erreur de connexion. Vérifiez vos identifiants.';
      },
    });
  }

  async startQrScanner(): Promise<void> {
    this.serverError = '';
    this.scanning = true;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      await new Promise(r => setTimeout(r, 100));
      const video = this.videoRef.nativeElement;
      video.srcObject = this.stream;
      video.setAttribute('playsinline', 'true');
      await video.play();
      this.scanLoop();
    } catch (err: any) {
      this.scanning = false;
      if (err.name === 'NotAllowedError') {
        this.serverError = 'Permission caméra refusée.';
      } else if (err.name === 'NotFoundError') {
        this.serverError = 'Aucune caméra détectée.';
      } else {
        this.serverError = 'Impossible d\'accéder à la caméra.';
      }
    }
  }

  private scanLoop(): void {
    const video = this.videoRef?.nativeElement;
    const canvas = this.canvasRef?.nativeElement;
    if (!video || !canvas || !this.scanning) return;

    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      const ctx = canvas.getContext('2d')!;
      canvas.height = video.videoHeight;
      canvas.width = video.videoWidth;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: 'dontInvert',
      });
      if (code) {
        this.stopScanner();
        try {
          const url = new URL(code.data);
          const token = url.searchParams.get('token');
          this.loginWithQrToken(token || code.data);
        } catch {
          this.loginWithQrToken(code.data);
        }
        return;
      }
    }
    this.animFrame = requestAnimationFrame(() => this.scanLoop());
  }

  stopScanner(): void {
    this.scanning = false;
    if (this.animFrame) cancelAnimationFrame(this.animFrame);
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
  }

  loginWithManualToken(): void {
    if (!this.manualToken.trim()) return;
    this.loginWithQrToken(this.manualToken.trim());
  }

  loginWithQrToken(qr_token: string): void {
    this.loading = true;
    this.scanning = false;
    this.serverError = '';

    this.http.post<any>(`${API_BASE}/auth/qr-login/`, { qr_token }).subscribe({
      next: (res) => {
        this.loading = false;
        localStorage.setItem('triage_jwt', res.token);
        localStorage.setItem('triage_user', JSON.stringify(res.user));
        this.auth.currentUser$.next(res.user);
        this.redirectAfterLogin();
      },
      error: (err) => {
        this.loading = false;
        this.serverError = err.error?.error || 'QR code invalide ou expiré.';
      }
    });
  }

  private redirectAfterLogin(): void {
    this.auth.isAdmin() ? this.router.navigate(['/admin']) : this.router.navigate(['/triage']);
  }

  ngOnDestroy(): void { this.stopScanner(); }
}