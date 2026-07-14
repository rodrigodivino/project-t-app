import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Workspace, WorkspacesService } from './workspaces.service';

@Component({
  selector: 'app-workspace-list',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="container">
        <header class="page-header">
          <h1>Workspaces</h1>
          <div class="create-row">
            <input
              type="text"
              [(ngModel)]="newName"
              placeholder="Nome do workspace"
              (keydown.enter)="onCreate()"
            />
            <button
              class="create-btn"
              (click)="onCreate()"
              [disabled]="!newName.trim()"
            >
              Criar
            </button>
          </div>
        </header>
        @if (workspaces.length === 0 && !loading) {
          <p class="empty">Nenhum workspace criado</p>
        }
        @if (workspaces.length > 0) {
          <ul class="ws-list">
            @for (ws of workspaces; track ws.id) {
              <li class="ws-item" (click)="onOpen(ws)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="1.5"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <span class="ws-name">{{ ws.name }}</span>
                <button
                  class="delete-btn"
                  (click)="onDelete($event, ws)"
                  aria-label="Remover"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2"
                       stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </li>
            }
          </ul>
        }
      </div>
    </div>
  `,
  styles: `
    .page {
      display: flex;
      justify-content: center;
      padding: 48px 24px;
      min-height: 100vh;
    }

    .container {
      width: 100%;
      max-width: 560px;
    }

    .page-header {
      margin-bottom: 32px;
    }

    .page-header h1 {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 16px;
    }

    .create-row {
      display: flex;
      gap: 8px;
    }

    .create-row input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      font-size: 0.9375rem;
      outline: none;
      background: var(--color-surface);
      color: var(--color-text);
    }

    .create-row input:focus {
      border-color: var(--color-border-focus);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    .create-btn {
      padding: 8px 16px;
      background: var(--color-accent);
      color: white;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.875rem;
      font-weight: 500;
      transition: background 0.15s;
    }

    .create-btn:hover:not(:disabled) {
      background: var(--color-accent-hover);
    }

    .create-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .empty {
      color: var(--color-text-secondary);
      font-size: 0.9375rem;
      text-align: center;
      padding: 48px 0;
    }

    .ws-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .ws-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background 0.1s;
    }

    .ws-item:hover {
      background: var(--color-accent-subtle);
    }

    .ws-item svg {
      flex-shrink: 0;
      color: var(--color-text-secondary);
    }

    .ws-name {
      flex: 1;
      font-size: 0.9375rem;
      font-weight: 500;
    }

    .delete-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border: none;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--color-text-secondary);
      opacity: 0;
      transition: opacity 0.15s, color 0.15s, background 0.15s;
    }

    .ws-item:hover .delete-btn {
      opacity: 1;
    }

    .delete-btn:hover {
      color: var(--color-error);
      background: var(--color-error-bg);
    }
  `,
})
export class WorkspaceList implements OnInit {
  workspaces: Workspace[] = [];
  newName = '';
  loading = false;

  constructor(
    private ws: WorkspacesService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loading = true;
    this.ws.list().subscribe({
      next: (list) => {
        this.workspaces = list;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  onCreate(): void {
    const name = this.newName.trim();
    if (!name) return;
    this.ws.create(name).subscribe((created) => {
      this.workspaces.unshift(created);
      this.newName = '';
    });
  }

  onOpen(workspace: Workspace): void {
    this.router.navigate(['/prototype', workspace.id]);
  }

  onDelete(event: Event, workspace: Workspace): void {
    event.stopPropagation();
    this.ws.delete(workspace.id).subscribe(() => {
      this.workspaces = this.workspaces.filter((w) => w.id !== workspace.id);
    });
  }
}
