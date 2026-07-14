import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { SourceDocument, SourcesService } from './sources.service';

@Component({
  selector: 'app-sources-modal',
  template: `
    <div class="backdrop" (click)="close.emit()"></div>
    <div class="modal">
      <header class="modal-header">
        <h2>Fontes externas</h2>
        <button class="close-btn" (click)="close.emit()" aria-label="Fechar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </header>
      <div class="modal-body">
        <div class="upload-area">
          <input
            #fileInput
            type="file"
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
            {{ uploading ? 'Enviando...' : 'Enviar documento' }}
          </button>
        </div>
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
          <ul class="doc-list">
            @for (doc of documents; track doc.id) {
              <li class="doc-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="doc-name">{{ doc.filename }}</span>
                <button class="delete-btn" (click)="onDelete(doc)" aria-label="Remover">
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
      width: 90%;
      max-width: 560px;
      max-height: 80vh;
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
      padding: 20px 24px;
      border-bottom: 1px solid var(--color-border);
    }

    .modal-header h2 {
      font-size: 1.125rem;
      font-weight: 600;
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
      padding: 24px;
    }

    .upload-area {
      margin-bottom: 16px;
    }

    .upload-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: var(--color-accent);
      color: white;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.875rem;
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

    .doc-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .doc-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      transition: background 0.1s;
    }

    .doc-item:hover {
      background: var(--color-accent-subtle);
    }

    .doc-item svg {
      flex-shrink: 0;
      color: var(--color-text-secondary);
    }

    .doc-name {
      flex: 1;
      font-size: 0.9375rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
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

    .doc-item:hover .delete-btn {
      opacity: 1;
    }

    .delete-btn:hover {
      color: var(--color-error);
      background: var(--color-error-bg);
    }
  `,
})
export class SourcesModal implements OnInit {
  @Input() workspaceId = '';
  @Output() close = new EventEmitter<void>();

  documents: SourceDocument[] = [];
  loading = false;
  uploading = false;

  constructor(private sources: SourcesService) {}

  ngOnInit(): void {
    this.loadDocuments();
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
