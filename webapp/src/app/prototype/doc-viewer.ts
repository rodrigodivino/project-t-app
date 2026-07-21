import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { marked } from 'marked';

@Component({
  selector: 'app-doc-viewer',
  template: `
    <div class="viewer-toolbar">
      <button class="back-btn" (click)="close.emit()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        Voltar
      </button>
      <span class="viewer-filename">{{ filename }}</span>
    </div>
    <div class="viewer-scroll">
      @if (loading) {
        <div class="viewer-status">Carregando...</div>
      }
      @if (error) {
        <div class="viewer-status viewer-error">Não foi possível carregar o documento</div>
      }
      @if (!loading && !error && renderedHtml) {
        <article class="prose" [innerHTML]="renderedHtml"></article>
      }
    </div>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .viewer-toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--color-border);
      flex-shrink: 0;
    }

    .back-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      color: var(--color-text);
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .back-btn:hover {
      border-color: var(--color-border-focus);
      box-shadow: var(--shadow-sm);
    }

    .viewer-filename {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .viewer-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 24px 32px;
      background: var(--color-surface);
    }

    .viewer-status {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
      padding: 32px;
      text-align: center;
    }

    .viewer-error {
      color: var(--color-error, #dc2626);
    }

    .prose {
      max-width: 72ch;
      margin: 0 auto;
      font-size: 0.9375rem;
      line-height: 1.7;
      color: var(--color-text);
    }

    .prose :first-child { margin-top: 0; }

    .prose h1, .prose h2, .prose h3, .prose h4 {
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      font-weight: 600;
      line-height: 1.3;
    }

    .prose h1 { font-size: 1.5rem; }
    .prose h2 { font-size: 1.25rem; }
    .prose h3 { font-size: 1.1rem; }

    .prose p { margin: 0.75em 0; }

    .prose ul, .prose ol {
      margin: 0.75em 0;
      padding-left: 1.5em;
    }

    .prose li { margin: 0.25em 0; }

    .prose table {
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
      font-size: 0.875rem;
      overflow-x: auto;
      display: block;
    }

    .prose th, .prose td {
      padding: 8px 12px;
      border: 1px solid var(--color-border);
      text-align: left;
    }

    .prose th {
      background: var(--color-bg);
      font-weight: 600;
    }

    .prose code {
      font-family: var(--font-mono, monospace);
      font-size: 0.85em;
      background: var(--color-bg);
      padding: 2px 5px;
      border-radius: 3px;
    }

    .prose pre {
      background: var(--color-bg);
      padding: 12px 16px;
      border-radius: var(--radius-sm);
      overflow-x: auto;
      margin: 1em 0;
    }

    .prose pre code {
      background: none;
      padding: 0;
    }

    .prose blockquote {
      border-left: 3px solid var(--color-border);
      margin: 1em 0;
      padding: 0.5em 1em;
      color: var(--color-text-secondary);
    }

    .prose hr {
      border: none;
      border-top: 1px solid var(--color-border);
      margin: 1.5em 0;
    }

    .prose a {
      color: var(--color-accent);
      text-decoration: underline;
    }
  `,
})
export class DocViewer implements OnChanges {
  @Input() url = '';
  @Input() filename = '';
  @Output() close = new EventEmitter<void>();

  loading = false;
  error = false;
  renderedHtml = '';

  constructor(private http: HttpClient) {}

  ngOnChanges(): void {
    if (this.url) {
      this.loadDocument();
    }
  }

  private loadDocument(): void {
    this.loading = true;
    this.error = false;
    this.renderedHtml = '';

    this.http.get(this.url, { responseType: 'text' }).subscribe({
      next: (markdown) => {
        this.renderedHtml = marked.parse(markdown, { async: false }) as string;
        this.loading = false;
      },
      error: () => {
        this.error = true;
        this.loading = false;
      },
    });
  }
}
