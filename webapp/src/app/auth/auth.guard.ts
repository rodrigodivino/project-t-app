import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth';
import { environment } from '../../environments/environment';

export const authGuard: CanActivateFn = () => {
  if (!environment.accessGate) {
    return true;
  }
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/']);
};
