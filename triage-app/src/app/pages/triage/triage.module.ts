import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TriagePage } from './triage.page';

const routes: Routes = [{ path: '', component: TriagePage }];

@NgModule({
  imports: [RouterModule.forChild(routes), TriagePage]
})
export class TriagePageModule {}