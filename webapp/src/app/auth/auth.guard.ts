import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth';
import { WebConfigService } from '../web-config';

export const authGuard: CanActivateFn = () => {
  if (!inject(WebConfigService).production) {
    return true;
  }
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/']);
};
