import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { environment } from '../environments/environment';

const gateRoute = {
  path: '',
  loadComponent: () => import('./access-gate').then((m) => m.AccessGate),
};

const prototypeRedirect = {
  path: '',
  redirectTo: 'prototype',
  pathMatch: 'full' as const,
};

export const routes: Routes = [
  environment.accessGate ? gateRoute : prototypeRedirect,
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () => import('./home').then((m) => m.Home),
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
