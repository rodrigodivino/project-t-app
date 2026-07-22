import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./access-gate').then((m) => m.AccessGate),
  },
  {
    path: 'prototype',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./prototype/workspace-list').then((m) => m.WorkspaceList),
  },
  {
    path: 'prototype/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./prototype/workbench').then((m) => m.Workbench),
  },
  { path: '**', redirectTo: '' },
];
