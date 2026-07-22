import { Component, EventEmitter, Input, Output, ViewChild, ElementRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import embed, { VisualizationSpec } from 'vega-embed';
import { SourcesService } from './sources.service';
import { ShoeboxService } from './shoebox.service';

@Component({
  selector: 'app-sources-modal',
  imports: [FormsModule],
  template: `
    <div class="backdrop" (click)="close.emit()"></div>
    <div class="modal">
      <header class="modal-header">
        <h2>Consultar Base de Dados</h2>
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
        <div class="query-section">
          <div class="schema-box">
            <div class="schema-title">Tabela <code>post_rede_social_himark</code></div>
            <div class="schema-desc">Posts de redes sociais da cidade de St. Himark, coletados entre 6 e 10 de abril de 2020.</div>
            <table class="schema-table">
              <thead><tr><th>Coluna</th><th>Tipo</th><th>Conteúdo</th></tr></thead>
              <tbody>
                <tr><td><code>time</code></td><td>TIMESTAMP</td><td>Data e hora do post</td></tr>
                <tr><td><code>location</code></td><td>TEXT</td><td>Distrito de origem do post</td></tr>
                <tr><td><code>account</code></td><td>TEXT</td><td>Nome de usuário do autor</td></tr>
                <tr><td><code>message</code></td><td>TEXT</td><td>Texto do post</td></tr>
              </tbody>
            </table>
          </div>
          <label for="sql-input">Consulta SQL</label>
          <textarea
            id="sql-input"
            [(ngModel)]="sql"
            [placeholder]="defaultQuery"
            rows="4"
            spellcheck="false"
          ></textarea>
          <div class="query-actions">
            <button class="exec-btn" (click)="runQuery()" [disabled]="executing">
              {{ executing ? 'Executando...' : 'Executar' }}
            </button>
            @if (results && results.length > 0) {
              <button class="add-btn" (click)="addToShoebox()" [disabled]="adding || !explanation.trim()">
                {{ adding ? 'Adicionando...' : 'Adicionar aos Resultados' }}
              </button>
            }
          </div>
        </div>
        @if (error) {
          <div class="error-msg">{{ error }}</div>
        }
        @if (results && results.length === 0 && !error) {
          <div class="empty-msg">Nenhum resultado encontrado</div>
        }
        @if (results && results.length > 0) {
          <div class="explanation-section">
            <label for="explanation-input">Explicação</label>
            <textarea
              id="explanation-input"
              [(ngModel)]="explanation"
              placeholder="O que esses resultados mostram e por que são relevantes..."
              rows="2"
            ></textarea>
          </div>
          @if (generatingChart) {
            <div class="chart-loading">Gerando visualização...</div>
          }
          @if (chartSpec) {
            <div class="chart-container" #modalChartContainer></div>
          }
          <div class="result-section">
            <div class="result-count">{{ results.length }} resultado(s)</div>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    @for (col of columns; track col) {
                      <th>{{ col }}</th>
                    }
                  </tr>
                </thead>
                <tbody>
                  @for (row of results; track $index) {
                    <tr>
                      @for (col of columns; track col) {
                        <td [class.col-message]="col === 'message'">{{ row[col] }}</td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
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
      width: 92%;
      max-width: 960px;
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
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .schema-box {
      padding: 12px 14px;
      background: var(--color-bg);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      font-size: 0.8125rem;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .schema-title {
      font-weight: 600;
      color: var(--color-text);
    }

    .schema-title code, .schema-table code {
      font-family: var(--font-mono, monospace);
      background: var(--color-surface);
      padding: 1px 5px;
      border-radius: 3px;
      font-size: 0.8125rem;
    }

    .schema-desc {
      color: var(--color-text-secondary);
      line-height: 1.4;
    }

    .schema-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 2px;
    }

    .schema-table th, .schema-table td {
      padding: 4px 8px;
      text-align: left;
      border-bottom: 1px solid var(--color-border);
      font-size: 0.8125rem;
    }

    .schema-table th {
      font-weight: 600;
      color: var(--color-text-secondary);
      background: transparent;
      position: static;
    }

    .schema-table td:nth-child(2) {
      font-family: var(--font-mono, monospace);
      color: var(--color-text-secondary);
    }

    .query-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .query-section label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
    }

    textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-bg);
      color: var(--color-text);
      font-family: var(--font-mono, monospace);
      font-size: 0.8125rem;
      line-height: 1.5;
      resize: vertical;
    }

    textarea:focus {
      outline: none;
      border-color: var(--color-accent);
      box-shadow: 0 0 0 2px var(--color-accent-subtle);
    }

    .query-actions {
      display: flex;
      gap: 8px;
    }

    .exec-btn, .add-btn {
      padding: 7px 14px;
      border: none;
      border-radius: var(--radius-sm);
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .exec-btn {
      background: var(--color-accent);
      color: white;
    }

    .exec-btn:hover:not(:disabled) {
      background: var(--color-accent-hover);
    }

    .add-btn {
      background: #22c55e;
      color: white;
    }

    .add-btn:hover:not(:disabled) {
      background: #16a34a;
    }

    .exec-btn:disabled, .add-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .explanation-section {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .explanation-section label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
    }

    .explanation-section textarea {
      font-family: inherit;
    }

    .chart-container {
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 12px;
      background: var(--color-bg);
      display: flex;
      justify-content: center;
    }

    .chart-loading {
      padding: 10px 14px;
      color: var(--color-text-secondary);
      font-size: 0.8125rem;
      font-style: italic;
    }

    .error-msg {
      padding: 10px 14px;
      background: var(--color-error-bg, #fef2f2);
      color: var(--color-error, #dc2626);
      border-radius: var(--radius-sm);
      font-size: 0.8125rem;
    }

    .empty-msg {
      padding: 10px 14px;
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    .result-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
      min-height: 0;
    }

    .result-count {
      font-size: 0.75rem;
      color: var(--color-text-secondary);
      font-weight: 500;
    }

    .table-scroll {
      flex: 1;
      overflow: auto;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8125rem;
    }

    th, td {
      padding: 6px 10px;
      border-bottom: 1px solid var(--color-border);
      text-align: left;
      vertical-align: top;
    }

    td.col-message {
      white-space: pre-wrap;
      word-break: break-word;
      min-width: 300px;
    }

    td:not(.col-message) {
      white-space: nowrap;
    }

    th {
      background: var(--color-bg);
      font-weight: 600;
      position: sticky;
      top: 0;
      z-index: 1;
      white-space: nowrap;
    }

    tr:hover td {
      background: var(--color-accent-subtle);
    }
  `,
})
export class SourcesModal {
  private chartContainerEl?: ElementRef<HTMLDivElement>;
  @ViewChild('modalChartContainer') set chartContainerRef(el: ElementRef<HTMLDivElement> | undefined) {
    this.chartContainerEl = el;
    if (el && this.chartSpec && this.results) {
      this.renderChart(this.chartSpec, this.results);
    }
  }

  @Input() workspaceId = '';
  @Output() close = new EventEmitter<void>();
  @Output() shoeboxChanged = new EventEmitter<void>();

  defaultQuery = "SELECT * FROM post_rede_social_himark WHERE time >= '2020-04-06 00:00' AND time < '2020-04-06 01:00'";
  sql = '';
  executedQuery = '';
  executing = false;
  adding = false;
  generatingChart = false;
  results: Record<string, any>[] | null = null;
  columns: string[] = [];
  explanation = '';
  chartSpec: Record<string, any> | null = null;
  error = '';

  constructor(
    private sources: SourcesService,
    private shoebox: ShoeboxService,
  ) {}

  runQuery(): void {
    this.executedQuery = this.sql.trim() || this.defaultQuery;
    this.executing = true;
    this.error = '';
    this.results = null;
    this.columns = [];
    this.chartSpec = null;
    this.sources.query(this.workspaceId, this.executedQuery).subscribe({
      next: (rows) => {
        this.results = rows;
        this.columns = rows.length > 0 ? Object.keys(rows[0]) : [];
        this.executing = false;
        if (rows.length > 0) {
          this.generateChart(rows);
        }
      },
      error: (err) => {
        this.error = err.error?.detail || 'Erro ao executar consulta';
        this.executing = false;
      },
    });
  }

  private generateChart(rows: Record<string, any>[]): void {
    this.generatingChart = true;
    this.shoebox
      .generateChart(this.workspaceId, this.executedQuery, this.explanation || this.executedQuery, rows)
      .subscribe({
        next: (resp) => {
          this.chartSpec = resp.chart_spec;
          this.generatingChart = false;
        },
        error: () => {
          this.generatingChart = false;
        },
      });
  }

  private renderChart(spec: Record<string, any>, data: Record<string, any>[]): void {
    if (!this.chartContainerEl) return;
    const fullSpec = { ...spec, data: { values: data } } as VisualizationSpec;
    embed(this.chartContainerEl.nativeElement, fullSpec, {
      actions: false,
      renderer: 'svg',
    }).catch(() => {});
  }

  addToShoebox(): void {
    if (!this.results || this.results.length === 0) return;
    this.adding = true;
    this.shoebox
      .add(
        this.workspaceId,
        this.executedQuery,
        this.explanation.trim(),
        this.results,
        this.chartSpec,
      )
      .subscribe({
        next: () => {
          this.adding = false;
          this.shoeboxChanged.emit();
        },
        error: () => {
          this.adding = false;
        },
      });
  }
}
