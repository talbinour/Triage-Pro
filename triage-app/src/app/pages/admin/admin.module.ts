import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AdminPage } from './admin.page';

const routes: Routes = [{ path: '', component: AdminPage }];

@NgModule({
  imports: [RouterModule.forChild(routes), AdminPage]
})
export class AdminPageModule {}