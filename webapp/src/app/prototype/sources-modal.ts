import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { SourceDocument, SourcesService } from './sources.service';
import { ShoeboxService } from './shoebox.service';
import { DocViewer } from './doc-viewer';

@Component({
  selector: 'app-sources-modal',
  imports: [DocViewer],
  template: `
    <div class="backdrop" (click)="close.emit()"></div>
    <div class="modal">
      @if (viewingDoc) {
        <app-doc-viewer
          [url]="viewingUrl"
          [filename]="viewingDoc.filename"
          (close)="viewingDoc = null"
        />
      } @else {
        <header class="modal-header">
          <h2>Todos os Documentos</h2>
          <div class="header-actions">
            <input
              #fileInput
              type="file"
              accept=".md,text/markdown"
              (change)="onFileSelected($event)"
              hidden
            />
            <button class="upload-btn" (click)="fileInput.click()" [disabled]="uploading">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              {{ uploading ? 'Enviando...' : 'Enviar' }}
            </button>
            <button class="close-btn" (click)="close.emit()" aria-label="Fechar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </header>
        <div class="modal-body">
          @if (documents.length === 0 && !loading) {
            <div class="empty-state">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="1.5"
                   stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <p>Nenhum documento adicionado</p>
            </div>
          }
          @if (documents.length > 0) {
            <div class="doc-grid">
              @for (doc of documents; track doc.id) {
                <div class="doc-card" [class.in-shoebox]="isInShoebox(doc.id)">
                  @if (isInShoebox(doc.id)) {
                    <div class="shoebox-badge">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="3"
                           stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </div>
                  }
                  <div class="card-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                      <polyline points="10 9 9 9 8 9"/>
                    </svg>
                  </div>
                  <div class="card-footer">
                    <span class="card-name" [title]="doc.filename">{{ doc.filename }}</span>
                  </div>
                  <div class="card-overlay">
                    <button class="action-btn view-btn" (click)="onView(doc)">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2"
                           stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                      Ver
                    </button>
                    <button
                      class="action-btn relevance-btn"
                      [disabled]="isInShoebox(doc.id)"
                      (click)="addToShoebox(doc)"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2"
                           stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      {{ isInShoebox(doc.id) ? 'Marcado' : 'Marcar Relevante' }}
                    </button>
                    <button class="action-btn delete-action" (click)="onDelete(doc)">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2"
                           stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                      Excluir
                    </button>
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: `
    :host {
      position: fixed;
      inset: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .backdrop {
      position: absolute;
      inset: 0;
      background: rgba(15, 23, 42, 0.4);
    }

    .modal {
      position: relative;
      width: 92%;
      max-width: 900px;
      height: 85vh;
      background: var(--color-surface);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid var(--color-border);
      flex-shrink: 0;
    }

    .modal-header h2 {
      font-size: 1.125rem;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .upload-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      background: var(--color-accent);
      color: white;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.8125rem;
      font-weight: 500;
      transition: background 0.15s;
    }

    .upload-btn:hover:not(:disabled) {
      background: var(--color-accent-hover);
    }

    .upload-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .close-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border: none;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--color-text-secondary);
      transition: background 0.15s, color 0.15s;
    }

    .close-btn:hover {
      background: var(--color-accent-subtle);
      color: var(--color-text);
    }

    .modal-body {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 48px 0;
      color: var(--color-text-secondary);
    }

    .empty-state p {
      font-size: 0.9375rem;
    }

    .doc-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
    }

    .doc-card {
      position: relative;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
      transition: box-shadow 0.15s, transform 0.15s;
    }

    .doc-card:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
    }

    .doc-card.in-shoebox {
      border-color: #22c55e;
    }

    .shoebox-badge {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 22px;
      height: 22px;
      background: #22c55e;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2;
    }

    .card-icon {
      aspect-ratio: 4 / 3;
      background: var(--color-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--color-text-secondary);
    }

    .card-footer {
      padding: 10px 12px;
      border-top: 1px solid var(--color-border);
    }

    .card-name {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--color-text);
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-overlay {
      position: absolute;
      inset: 0;
      background: rgba(15, 23, 42, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 12px;
      opacity: 0;
      transition: opacity 0.15s;
    }

    .doc-card:hover .card-overlay {
      opacity: 1;
    }

    .action-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      width: 100%;
      padding: 7px 12px;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.1s;
    }

    .view-btn {
      background: white;
      color: var(--color-text);
    }

    .view-btn:hover {
      background: #f0f0f0;
    }

    .relevance-btn {
      background: #22c55e;
      color: white;
    }

    .relevance-btn:hover:not(:disabled) {
      background: #16a34a;
    }

    .relevance-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .delete-action {
      background: transparent;
      color: rgba(255, 255, 255, 0.7);
    }

    .delete-action:hover {
      color: #fca5a5;
      background: rgba(220, 38, 38, 0.2);
    }
  `,
})
export class SourcesModal implements OnInit {
  @Input() workspaceId = '';
  @Input() shoeboxDocIds: Set<string> = new Set();
  @Output() close = new EventEmitter<void>();
  @Output() shoeboxChanged = new EventEmitter<void>();

  documents: SourceDocument[] = [];
  loading = false;
  uploading = false;
  viewingDoc: SourceDocument | null = null;
  viewingUrl = '';

  constructor(
    private sources: SourcesService,
    private shoebox: ShoeboxService,
  ) {}

  ngOnInit(): void {
    this.loadDocuments();
  }

  isInShoebox(docId: string): boolean {
    return this.shoeboxDocIds.has(docId);
  }

  onView(doc: SourceDocument): void {
    this.viewingUrl = this.sources.contentUrl(this.workspaceId, doc.id);
    this.viewingDoc = doc;
  }

  addToShoebox(doc: SourceDocument): void {
    if (this.isInShoebox(doc.id)) return;
    this.shoebox.add(this.workspaceId, doc.id).subscribe(() => {
      this.shoeboxDocIds.add(doc.id);
      this.shoeboxChanged.emit();
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    this.uploading = true;
    this.sources.upload(this.workspaceId, file).subscribe({
      next: (doc) => {
        this.documents.unshift(doc);
        this.uploading = false;
        input.value = '';
      },
      error: () => {
        this.uploading = false;
        input.value = '';
      },
    });
  }

  onDelete(doc: SourceDocument): void {
    this.sources.delete(this.workspaceId, doc.id).subscribe(() => {
      this.documents = this.documents.filter((d) => d.id !== doc.id);
      if (this.shoeboxDocIds.has(doc.id)) {
        this.shoeboxDocIds.delete(doc.id);
        this.shoeboxChanged.emit();
      }
    });
  }

  private loadDocuments(): void {
    this.loading = true;
    this.sources.list(this.workspaceId).subscribe({
      next: (docs) => {
        this.documents = docs;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }
}
