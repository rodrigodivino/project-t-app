import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { SourcesModal } from './sources-modal';
import { SourceDocument, SourcesService } from './sources.service';
import { ShoeboxItem, ShoeboxService } from './shoebox.service';

interface ShoeboxEntry {
  item: ShoeboxItem;
  filename: string;
}

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
            @if (shoeboxEntries.length === 0) {
              <p class="placeholder">Selecione documentos nas Fontes</p>
            }
            @for (entry of shoeboxEntries; track entry.item.id) {
              <div class="shoebox-card">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="card-name">{{ entry.filename }}</span>
                <button class="card-remove" (click)="removeFromShoebox(entry)" aria-label="Remover">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2.5"
                       stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            }
          </div>
        </section>
      </div>
    </div>
    @if (sourcesOpen) {
      <app-sources-modal
        [workspaceId]="workspaceId"
        [shoeboxDocIds]="shoeboxDocIds"
        (shoeboxChanged)="loadShoebox()"
        (close)="sourcesOpen = false"
      />
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
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow-y: auto;
    }

    .placeholder {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
      padding: 4px;
    }

    .shoebox-card {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .shoebox-card:hover {
      border-color: var(--color-border-focus);
      box-shadow: var(--shadow-sm);
    }

    .shoebox-card svg {
      flex-shrink: 0;
      color: var(--color-text-secondary);
    }

    .card-name {
      flex: 1;
      font-size: 0.875rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-remove {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      border: none;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--color-text-secondary);
      opacity: 0;
      transition: opacity 0.15s, color 0.15s, background 0.15s;
    }

    .shoebox-card:hover .card-remove {
      opacity: 1;
    }

    .card-remove:hover {
      color: var(--color-error);
      background: var(--color-error-bg);
    }
  `,
})
export class Workbench implements OnInit {
  workspaceId = '';
  sourcesOpen = false;
  shoeboxEntries: ShoeboxEntry[] = [];
  shoeboxDocIds = new Set<string>();

  private allDocuments: SourceDocument[] = [];

  constructor(
    private route: ActivatedRoute,
    private shoeboxSvc: ShoeboxService,
    private sourcesSvc: SourcesService,
  ) {}

  ngOnInit(): void {
    this.workspaceId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadSources();
  }

  loadShoebox(): void {
    this.shoeboxSvc.list(this.workspaceId).subscribe((items) => {
      this.shoeboxDocIds = new Set(items.map((i) => i.source_document_id));
      this.shoeboxEntries = items.map((item) => ({
        item,
        filename: this.filenameFor(item.source_document_id),
      }));
    });
  }

  removeFromShoebox(entry: ShoeboxEntry): void {
    this.shoeboxSvc
      .remove(this.workspaceId, entry.item.source_document_id)
      .subscribe(() => {
        this.shoeboxDocIds.delete(entry.item.source_document_id);
        this.shoeboxEntries = this.shoeboxEntries.filter(
          (e) => e.item.id !== entry.item.id
        );
      });
  }

  private loadSources(): void {
    this.sourcesSvc.list(this.workspaceId).subscribe((docs) => {
      this.allDocuments = docs;
      this.loadShoebox();
    });
  }

  private filenameFor(docId: string): string {
    return (
      this.allDocuments.find((d) => d.id === docId)?.filename ?? 'Documento'
    );
  }
}
