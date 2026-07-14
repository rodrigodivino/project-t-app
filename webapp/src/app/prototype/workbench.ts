import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { SourcesModal } from './sources-modal';

@Component({
  selector: 'app-workbench',
  imports: [SourcesModal],
  template: `
    <div class="workbench">
      <header class="workbench-header">
        <h1>Prototype</h1>
        <button class="sources-btn" (click)="sourcesOpen = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          Fontes
        </button>
      </header>
      <div class="workbench-board">
        <section class="board-column">
          <h2>Shoebox</h2>
          <div class="column-body">
            <p class="placeholder">Documentos selecionados</p>
          </div>
        </section>
      </div>
    </div>
    @if (sourcesOpen) {
      <app-sources-modal [workspaceId]="workspaceId" (close)="sourcesOpen = false" />
    }
  `,
  styles: `
    .workbench {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }

    .workbench-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      border-bottom: 1px solid var(--color-border);
      background: var(--color-surface);
    }

    .workbench-header h1 {
      font-size: 1.25rem;
      font-weight: 600;
    }

    .sources-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      color: var(--color-text);
      font-size: 0.875rem;
      font-weight: 500;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .sources-btn:hover {
      border-color: var(--color-border-focus);
      box-shadow: var(--shadow-sm);
    }

    .workbench-board {
      display: flex;
      flex: 1;
      gap: 1px;
      background: var(--color-border);
      overflow-x: auto;
    }

    .board-column {
      flex: 1;
      min-width: 280px;
      background: var(--color-bg);
      display: flex;
      flex-direction: column;
    }

    .board-column h2 {
      font-size: 0.8125rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-text-secondary);
      padding: 12px 16px;
      border-bottom: 1px solid var(--color-border);
    }

    .column-body {
      flex: 1;
      padding: 16px;
    }

    .placeholder {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }
  `,
})
export class Workbench implements OnInit {
  workspaceId = '';
  sourcesOpen = false;

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.workspaceId = this.route.snapshot.paramMap.get('id') ?? '';
  }
}
