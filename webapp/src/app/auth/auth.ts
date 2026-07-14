import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private authenticated = false;

  constructor(private http: HttpClient) {
    this.authenticated = sessionStorage.getItem('authenticated') === 'true';
  }

  verify(code: string): Observable<boolean> {
    return this.http
      .post<{ valid: boolean }>('/api/auth/verify', { code })
      .pipe(
        map((res) => res.valid),
        tap((valid) => {
          this.authenticated = valid;
          if (valid) {
            sessionStorage.setItem('authenticated', 'true');
          }
        })
      );
  }

  isAuthenticated(): boolean {
    return this.authenticated;
  }
}
