import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { SourcesModal } from './sources-modal';
import { ShoeboxItem, ShoeboxService } from './shoebox.service';
import { DocViewer } from './doc-viewer';

@Component({
  selector: 'app-workbench',
  imports: [SourcesModal, DocViewer],
  template: `
    <div class="workbench">
      <header class="workbench-header">
        <h1>Prototype</h1>
      </header>
      <div class="workbench-board">
        <section class="board-column">
          <h2>Documentos Relevantes</h2>
          <div class="column-body">
            <button class="all-docs-btn" (click)="sourcesOpen = true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              Ver Todos os Documentos
            </button>
            @if (shoeboxItems.length === 0) {
              <p class="placeholder">Nenhum documento marcado como relevante</p>
            }
            @for (item of shoeboxItems; track item.id) {
              <div class="shoebox-card" (click)="viewDoc(item)">
                <div class="card-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="1.5"
                       stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                </div>
                <div class="card-info">
                  <span class="card-name" [title]="item.filename">{{ item.filename }}</span>
                </div>
                <button
                  class="card-remove"
                  (click)="removeFromShoebox($event, item)"
                  aria-label="Remover"
                >
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
    @if (viewingItem) {
      <div class="doc-modal-backdrop" (click)="viewingItem = null"></div>
      <div class="doc-modal">
        <app-doc-viewer
          [url]="viewingContentUrl"
          [filename]="viewingItem.filename"
          (close)="viewingItem = null"
        />
      </div>
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

    .workbench-board {
      display: flex;
      flex: 1;
      overflow-x: auto;
    }

    .board-column {
      width: 300px;
      flex-shrink: 0;
      background: var(--color-surface);
      border-right: 1px solid var(--color-border);
      display: flex;
      flex-direction: column;
    }

    .board-column h2 {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
      padding: 14px 16px;
      border-bottom: 1px solid var(--color-border);
    }

    .column-body {
      flex: 1;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow-y: auto;
    }

    .all-docs-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 9px 10px;
      background: var(--color-bg);
      border: 1px dashed var(--color-border);
      border-radius: var(--radius-sm);
      color: var(--color-text-secondary);
      font-size: 0.8125rem;
      font-weight: 500;
      transition: border-color 0.15s, color 0.15s, box-shadow 0.15s;
    }

    .all-docs-btn:hover {
      border-color: var(--color-accent);
      color: var(--color-accent);
      box-shadow: var(--shadow-sm);
    }

    .placeholder {
      color: var(--color-text-secondary);
      font-size: 0.8125rem;
      padding: 8px 6px;
    }

    .shoebox-card {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      background: var(--color-surface);
      border-radius: var(--radius-sm);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      cursor: pointer;
      transition: box-shadow 0.15s, transform 0.15s;
    }

    .shoebox-card:hover {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
      transform: translateY(-1px);
    }

    .card-icon {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      color: var(--color-text-secondary);
    }

    .card-info {
      flex: 1;
      min-width: 0;
    }

    .card-name {
      font-size: 0.8125rem;
      font-weight: 500;
      display: block;
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
      flex-shrink: 0;
      transition: opacity 0.15s, color 0.15s, background 0.15s;
    }

    .shoebox-card:hover .card-remove {
      opacity: 1;
    }

    .card-remove:hover {
      color: var(--color-error);
      background: var(--color-error-bg);
    }

    .doc-modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(15, 23, 42, 0.4);
    }

    .doc-modal {
      position: fixed;
      inset: 0;
      z-index: 101;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
    }

    .doc-modal app-doc-viewer {
      width: 92%;
      max-width: 900px;
      height: 85vh;
      background: var(--color-surface);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      overflow: hidden;
      pointer-events: auto;
    }
  `,
})
export class Workbench implements OnInit {
  workspaceId = '';
  sourcesOpen = false;
  shoeboxItems: ShoeboxItem[] = [];
  shoeboxDocIds = new Set<string>();
  viewingItem: ShoeboxItem | null = null;
  viewingContentUrl = '';

  constructor(
    private route: ActivatedRoute,
    private shoeboxSvc: ShoeboxService,
  ) {}

  ngOnInit(): void {
    this.workspaceId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadShoebox();
  }

  viewDoc(item: ShoeboxItem): void {
    this.viewingContentUrl = this.shoeboxSvc.contentUrl(
      this.workspaceId,
      item.source_document_id,
    );
    this.viewingItem = item;
  }

  loadShoebox(): void {
    this.shoeboxSvc.list(this.workspaceId).subscribe((items) => {
      this.shoeboxDocIds = new Set(items.map((i) => i.source_document_id));
      this.shoeboxItems = items;
    });
  }

  removeFromShoebox(event: Event, item: ShoeboxItem): void {
    event.stopPropagation();
    this.shoeboxSvc
      .remove(this.workspaceId, item.source_document_id)
      .subscribe(() => {
        this.shoeboxDocIds.delete(item.source_document_id);
        this.shoeboxItems = this.shoeboxItems.filter(
          (i) => i.id !== item.id
        );
      });
  }
}
