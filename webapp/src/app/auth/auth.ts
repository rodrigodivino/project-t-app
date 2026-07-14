import { Injectable } from '@angular/core';
import {
  HttpClient,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private authenticated = false;
  private code = '';

  constructor(private http: HttpClient) {
    const stored = sessionStorage.getItem('access_code');
    if (stored) {
      this.authenticated = true;
      this.code = stored;
    }
  }

  verify(code: string): Observable<boolean> {
    return this.http
      .post<{ valid: boolean }>('/api/auth/verify', { code })
      .pipe(
        map((res) => res.valid),
        tap((valid) => {
          this.authenticated = valid;
          if (valid) {
            this.code = code;
            sessionStorage.setItem('access_code', code);
          }
        })
      );
  }

  isAuthenticated(): boolean {
    return this.authenticated;
  }

  getCode(): string {
    return this.code;
  }
}

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private auth: AuthService) {}

  intercept(
    req: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    const code = this.auth.getCode();
    if (code) {
      const cloned = req.clone({
        setHeaders: { Authorization: code },
      });
      return next.handle(cloned);
    }
    return next.handle(req);
  }
}
