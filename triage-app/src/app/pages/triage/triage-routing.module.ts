import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { TriagePage } from './triage.page';

const routes: Routes = [
  {
    path: '',
    component: TriagePage
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TriagePageRoutingModule {}
