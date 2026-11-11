import { NgModule } from '@angular/core';
import { PreloadAllModules, RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './guards/auth.guard';

const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  {
    path: 'login',
    loadChildren: () => import('./pages/login/login.module').then(m => m.LoginPageModule)
  },
  {
    path: 'admin',
    loadChildren: () => import('./pages/admin/admin.module').then(m => m.AdminPageModule),
    canActivate: [AuthGuard],
    data: { requireAdmin: true }
  },
  {
    path: 'profil',
    loadChildren: () => import('./pages/profil/profil.module').then(m => m.ProfilPageModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'triage',
    loadChildren: () => import('./pages/triage/triage.module').then(m => m.TriagePageModule),
    canActivate: [AuthGuard]
  },
  { path: '**', redirectTo: 'login' },
  
  
 
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { preloadingStrategy: PreloadAllModules })],
  exports: [RouterModule]
})
export class AppRoutingModule {}