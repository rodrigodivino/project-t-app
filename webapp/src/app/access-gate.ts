import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from './auth/auth';
import { WebConfigService } from './web-config';

@Component({
  selector: 'app-access-gate',
  imports: [FormsModule],
  template: `
    <div class="gate-wrapper">
      <div class="gate-card">
        <div class="gate-header">
          <div class="gate-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <h2>Área restrita</h2>
          <p class="gate-subtitle">
            Insira o código recebido por e-mail para acessar o estudo.
          </p>
        </div>

        <div class="gate-form">
          <label for="code">Código de acesso</label>
          <input
            id="code"
            type="text"
            [(ngModel)]="code"
            placeholder="Ex: abc123"
            (keydown.enter)="submit()"
            [class.input-error]="error"
            autocomplete="off"
            spellcheck="false"
          />
          @if (error) {
            <p class="error-msg">Código inválido. Verifique e tente novamente.</p>
          }
          <button (click)="submit()" [disabled]="loading || !code.trim()">
            {{ loading ? 'Verificando...' : 'Entrar' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: `
    .gate-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 24px;
    }

    .gate-card {
      width: 100%;
      max-width: 400px;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-lg);
      padding: 40px 32px;
      box-shadow: var(--shadow-md);
    }

    .gate-header {
      text-align: center;
      margin-bottom: 32px;
    }

    .gate-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      border-radius: var(--radius-md);
      background: var(--color-accent-subtle);
      color: var(--color-accent);
      margin-bottom: 20px;
    }

    h2 {
      font-size: 1.375rem;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .gate-subtitle {
      color: var(--color-text-secondary);
      font-size: 0.9375rem;
      line-height: 1.5;
    }

    .gate-form {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-secondary);
    }

    input {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      font-size: 0.9375rem;
      outline: none;
      transition: border-color 0.15s;
      background: var(--color-surface);
      color: var(--color-text);
    }

    input:focus {
      border-color: var(--color-border-focus);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    input.input-error {
      border-color: var(--color-error);
    }

    input.input-error:focus {
      box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
    }

    .error-msg {
      color: var(--color-error);
      font-size: 0.8125rem;
      margin-top: 2px;
    }

    button {
      margin-top: 16px;
      padding: 10px 20px;
      background: var(--color-accent);
      color: white;
      border: none;
      border-radius: var(--radius-sm);
      font-weight: 500;
      font-size: 0.9375rem;
      transition: background 0.15s;
    }

    button:hover:not(:disabled) {
      background: var(--color-accent-hover);
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    button:focus-visible {
      outline: 2px solid var(--color-accent);
      outline-offset: 2px;
    }
  `,
})
export class AccessGate implements OnInit {
  code = '';
  error = false;
  loading = false;

  constructor(
    private auth: AuthService,
    private router: Router,
    private config: WebConfigService,
  ) {}

  ngOnInit(): void {
    if (!this.config.production) {
      this.router.navigate(['/prototype']);
      return;
    }
    if (this.auth.isAuthenticated()) {
      this.router.navigate(['/prototype']);
    }
  }

  submit(): void {
    if (!this.code.trim() || this.loading) return;
    this.loading = true;
    this.error = false;
    this.auth.verify(this.code).subscribe({
      next: (valid) => {
        this.loading = false;
        if (valid) {
          this.router.navigate(['/prototype']);
        } else {
          this.error = true;
        }
      },
      error: () => {
        this.loading = false;
        this.error = true;
      },
    });
  }
}
