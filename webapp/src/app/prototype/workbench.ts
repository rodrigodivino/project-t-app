import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import embed, { VisualizationSpec } from 'vega-embed';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { SourcesModal } from './sources-modal';
import {
  ShoeboxItemFull,
  ShoeboxItemSummary,
  ShoeboxService,
} from './shoebox.service';
import {
  EvidenceItemFull,
  EvidenceItemSummary,
  EvidenceService,
} from './evidence.service';
import {
  SchematizationData,
  SchematizationService,
} from './schematization.service';

@Component({
  selector: 'app-workbench',
  imports: [SourcesModal, FormsModule],
  template: `
    <div class="workbench">
      <header class="workbench-header">
        <h1>Prototype</h1>
      </header>
      <div class="workbench-board">
        <section class="board-column">
          <h2>
            Resultados
            <button class="ai-search-btn"
                    [class.ai-search-cooking]="aiCooking"
                    [disabled]="aiCooking"
                    (click)="triggerAiSearch()"
                    title="Busca IA">
              <svg class="sparkle-icon" width="14" height="14" viewBox="0 0 24 24"
                   fill="currentColor" stroke="none">
                <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
              </svg>
            </button>
          </h2>
          @if (aiCooking) {
            <div class="ai-shimmer"></div>
          }
          <div class="column-body">
            <button class="all-docs-btn" (click)="sourcesOpen = true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              Consultar Base de Dados
            </button>
            @if (shoeboxItems.length === 0) {
              <p class="placeholder">Nenhum resultado adicionado</p>
            }
            @for (item of shoeboxItems; track item.id) {
              <div class="shoebox-card"
                   [class.shoebox-card-ai]="item.ai_authored"
                   [class.shoebox-card-new]="newShoeboxIds.has(item.id)"
                   (click)="viewItem(item)">
                @if (unseenShoeboxIds.has(item.id)) {
                  <span class="notif-dot"></span>
                }
                <div class="card-icon">
                  @if (item.ai_authored) {
                    <svg class="sparkle-icon"
                         [class.sparkle-pulse]="newShoeboxIds.has(item.id)"
                         width="20" height="20" viewBox="0 0 24 24"
                         fill="var(--color-accent)" stroke="none">
                      <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
                    </svg>
                  } @else {
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                      <ellipse cx="12" cy="5" rx="9" ry="3"/>
                      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                    </svg>
                  }
                </div>
                <div class="card-info">
                  <span class="card-name" [title]="item.explanation">{{ item.explanation }}</span>
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

        <section class="board-column">
          <h2>Evidências</h2>
          @if (evidenceCooking) {
            <div class="ai-shimmer"></div>
          }
          <div class="column-body">
            @if (filteredEvidence.length === 0) {
              <p class="placeholder">Nenhuma evidência extraída</p>
            }
            @for (item of filteredEvidence; track item.id) {
              <div
                class="evidence-card"
                [class.evidence-ai]="isUncertain(item)"
                [class.evidence-card-new]="newEvidenceIds.has(item.id)"
                [draggable]="isDraggable(item)"
                (dragstart)="onDragStart($event, item)"
                (click)="viewEvidenceItem(item)"
              >
                @if (unseenEvidenceIds.has(item.id)) {
                  <span class="notif-dot"></span>
                }
                <div class="card-icon">
                  @if (item.ai_authored) {
                    <svg class="sparkle-icon"
                         [class.sparkle-pulse]="newEvidenceIds.has(item.id)"
                         width="20" height="20" viewBox="0 0 24 24"
                         fill="var(--color-accent)" stroke="none">
                      <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
                    </svg>
                  } @else {
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                  }
                </div>
                <div class="card-info">
                  <span class="card-name" [title]="item.content">{{ item.content }}</span>
                  @if (isUncertain(item)) {
                    <span class="ai-badge">IA · a verificar</span>
                  }
                </div>
                <button
                  class="card-remove"
                  (click)="removeEvidence($event, item)"
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

        <section
          class="board-column schema-column"
          [class.schema-dragover]="schemaDragover"
          (dragover)="onSchemaDragover($event)"
          (dragleave)="onSchemaDragleave($event)"
          (drop)="onSchemaDrop($event)"
        >
          <h2>Esquematização</h2>
          <div class="column-body">
            @if (schemaEvidence.length === 0 && !schemaDragover) {
              <p class="placeholder">Arraste evidências para cá</p>
            }
            @for (item of schemaEvidence; track item.id) {
              <div class="evidence-card schema-evidence-card" (click)="viewEvidenceItem(item)">
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
                  <span class="card-name" [title]="item.content">{{ item.content }}</span>
                </div>
                <button
                  class="card-remove"
                  (click)="removeFromSchema($event, item)"
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
        (shoeboxChanged)="loadShoebox()"
        (close)="sourcesOpen = false"
      />
    }
    @if (viewingDetail) {
      <div class="detail-backdrop" (click)="closeDetail()"></div>
      <div class="detail-modal">
        <header class="detail-header">
          <button class="back-btn" (click)="closeDetail()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
            Voltar
          </button>
          @if (selectedRows.size > 0 && !addingEvidence) {
            <button class="add-evidence-btn" (click)="addingEvidence = true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Adicionar Evidência ({{ selectedRows.size }})
            </button>
          }
        </header>
        <div class="detail-body">
          @if (addingEvidence) {
            <div class="evidence-form">
              <label>Escreva a evidência observada nas linhas selecionadas</label>
              <textarea
                class="evidence-textarea"
                [(ngModel)]="evidenceText"
                rows="3"
                placeholder="Descreva a evidência factual observada nos dados..."
              ></textarea>
              <div class="evidence-form-actions">
                <button class="form-cancel" (click)="addingEvidence = false; evidenceText = ''">
                  Cancelar
                </button>
                <button
                  class="form-confirm"
                  [disabled]="!evidenceText.trim()"
                  (click)="confirmAddEvidence()"
                >
                  Confirmar
                </button>
              </div>
            </div>
          }
          <div class="detail-field">
            <label>Consulta</label>
            <pre class="detail-query">{{ viewingDetail.query }}</pre>
          </div>
          <div class="detail-field">
            <label>Explicação</label>
            <p class="detail-explanation">{{ viewingDetail.explanation }}</p>
          </div>
          @if (viewingDetail.chart_spec) {
            <div class="detail-field">
              <label>Visualização</label>
              <div class="chart-container" #chartContainer></div>
            </div>
          }
          <div class="detail-field">
            <label>Resultado ({{ viewingDetail.result.length }} linha(s))</label>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th class="col-check">
                      <label class="check-wrap">
                        <input
                          type="checkbox"
                          [checked]="allRowsSelected()"
                          (change)="toggleAllRows()"
                        />
                        <span class="checkmark"></span>
                      </label>
                    </th>
                    @for (col of detailColumns; track col) {
                      <th>{{ col }}</th>
                    }
                  </tr>
                </thead>
                <tbody>
                  @for (row of viewingDetail.result; track $index) {
                    <tr [class.row-selected]="selectedRows.has($index)">
                      <td class="col-check">
                        <label class="check-wrap">
                          <input
                            type="checkbox"
                            [checked]="selectedRows.has($index)"
                            (change)="toggleRow($index)"
                          />
                          <span class="checkmark"></span>
                        </label>
                      </td>
                      @for (col of detailColumns; track col) {
                        <td [class.col-message]="col === 'message'">{{ row[col] }}</td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    }
    @if (viewingEvidence) {
      <div class="detail-backdrop" (click)="closeEvidenceDetail()"></div>
      <div class="detail-modal">
        <header class="detail-header">
          <button class="back-btn" (click)="closeEvidenceDetail()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
            Voltar
          </button>
          @if (isUncertain(viewingEvidence) && !correctingEvidence) {
            <div class="header-actions">
              <button class="action-btn action-reject" (click)="rejectEvidence()">
                Rejeitar
              </button>
              <button class="action-btn action-correct" (click)="startCorrecting()">
                Corrigir
              </button>
              @if (verifyCountdown > 0) {
                <button class="action-btn action-approve action-disabled" disabled>
                  Aprovar ({{ verifyCountdown }}s)
                </button>
              } @else {
                <button class="action-btn action-approve" (click)="approveEvidence()">
                  Aprovar
                </button>
              }
            </div>
          }
          @if (correctingEvidence) {
            <div class="header-actions">
              <button class="action-btn action-correct-cancel" (click)="cancelCorrecting()">
                Cancelar
              </button>
              <button
                class="action-btn action-correct-save"
                [disabled]="!correctText.trim()"
                (click)="saveCorrectedEvidence()"
              >
                Salvar
              </button>
            </div>
          }
        </header>
        <div class="detail-body">
          <div class="detail-field">
            <label>Evidência</label>
            @if (correctingEvidence) {
              <textarea
                class="evidence-textarea"
                [(ngModel)]="correctText"
                rows="3"
              ></textarea>
            } @else {
              <div class="evidence-content-box" [class.evidence-content-ai]="isUncertain(viewingEvidence)">
                <p class="detail-explanation">{{ viewingEvidence.content }}</p>
                @if (isUncertain(viewingEvidence)) {
                  <span class="ai-badge-inline">IA · a verificar</span>
                }
              </div>
            }
          </div>
          @if (evidenceSourceExplanation) {
            <div class="detail-field">
              <label>Explicação do Resultado</label>
              <p class="detail-explanation">{{ evidenceSourceExplanation }}</p>
            </div>
          }
          @if (evidenceSourceData) {
            <div class="detail-field">
              <label>Dados ({{ evidenceSourceData.length }} linha(s))</label>
              <div class="table-scroll">
                <table>
                  <thead>
                    <tr>
                      @for (col of evidenceSourceColumns; track col) {
                        <th>{{ col }}</th>
                      }
                    </tr>
                  </thead>
                  <tbody>
                    @for (row of evidenceSourceData; track $index) {
                      <tr>
                        @for (col of evidenceSourceColumns; track col) {
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

    .schema-column {
      width: auto;
      flex: 1;
      min-width: 300px;
      border-right: none;
    }

    .schema-dragover {
      background: var(--color-accent-subtle);
    }

    .schema-dragover .column-body {
      outline: 2px dashed var(--color-accent);
      outline-offset: -4px;
      border-radius: var(--radius-sm);
    }

    .schema-evidence-card .card-icon {
      color: var(--color-accent);
    }

    [draggable="true"] {
      cursor: grab;
    }

    [draggable="true"]:active {
      cursor: grabbing;
    }

    .board-column h2 {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
      padding: 14px 16px;
      border-bottom: 1px solid var(--color-border);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ai-search-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border: none;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--color-text-secondary);
      cursor: pointer;
      transition: color 0.15s, background 0.15s;
      margin-left: auto;
      padding: 0;
    }

    .ai-search-btn:hover:not(:disabled) {
      color: var(--color-accent);
      background: var(--color-accent-subtle);
    }

    .ai-search-btn:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }

    .ai-search-cooking .sparkle-icon {
      color: var(--color-accent);
      animation: sparkle-spin 0.8s ease-in-out infinite;
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

    .shoebox-card,
    .evidence-card {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 10px;
      background: var(--color-surface);
      border-radius: var(--radius-sm);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      cursor: pointer;
      transition: box-shadow 0.15s, transform 0.15s;
      position: relative;
    }

    .notif-dot {
      position: absolute;
      top: -3px;
      right: -3px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--color-accent);
      box-shadow: 0 0 0 2px var(--color-surface);
    }

    @keyframes shimmer-sweep {
      0% { background-position: -300px 0; }
      100% { background-position: 300px 0; }
    }

    .ai-shimmer {
      height: 2px;
      background: linear-gradient(
        90deg,
        transparent 0%,
        var(--color-accent) 50%,
        transparent 100%
      );
      background-size: 300px 2px;
      animation: shimmer-sweep 2s ease-in-out infinite;
    }

    .shoebox-card-ai {
      border-left: 3px solid var(--color-accent);
    }

    .shoebox-card-ai .card-name {
      font-family: inherit;
      white-space: normal;
    }

    @keyframes card-fade-in {
      0% { opacity: 0; }
      100% { opacity: 1; }
    }

    @keyframes glow-fade {
      0%, 60% {
        box-shadow: 0 0 0 1.5px var(--color-accent),
                    0 2px 10px rgba(99, 102, 241, 0.18);
      }
      100% {
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }
    }

    @keyframes sparkle-spin {
      0%, 100% { opacity: 0.7; transform: scale(0.85) rotate(0deg); }
      50% { opacity: 1; transform: scale(1.15) rotate(15deg); }
    }

    .shoebox-card-new {
      animation: card-fade-in 0.8s ease-out,
                 glow-fade 2.5s ease-out forwards;
    }

    .sparkle-pulse {
      animation: sparkle-spin 0.8s ease-in-out 3;
    }

    .shoebox-card:hover,
    .evidence-card:hover {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
      transform: translateY(-1px);
    }

    .evidence-card .card-icon {
      color: var(--color-accent);
    }

    .evidence-card-new {
      animation: card-fade-in 0.8s ease-out,
                 glow-fade 2.5s ease-out forwards;
    }

    .evidence-ai {
      border-left: 3px solid var(--color-warning);
      background: var(--color-warning-bg);
    }

    .evidence-ai .card-icon {
      color: var(--color-warning);
    }

    .ai-badge {
      display: inline-block;
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--color-warning);
      background: rgba(217, 119, 6, 0.1);
      padding: 1px 6px;
      border-radius: 3px;
      margin-top: 2px;
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
      font-size: 0.75rem;
      font-weight: 500;
      font-family: var(--font-mono, monospace);
      display: block;
      line-height: 1.4;
    }

    .evidence-card .card-name {
      font-family: inherit;
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

    .shoebox-card:hover .card-remove,
    .evidence-card:hover .card-remove {
      opacity: 1;
    }

    .card-remove:hover {
      color: var(--color-error);
      background: var(--color-error-bg);
    }

    .detail-backdrop {
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(15, 23, 42, 0.4);
    }

    .detail-modal {
      position: fixed;
      inset: 0;
      z-index: 101;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      pointer-events: none;
    }

    .detail-modal header,
    .detail-modal .detail-body {
      pointer-events: auto;
    }

    .detail-header {
      width: 92%;
      max-width: 960px;
      background: var(--color-surface);
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
      padding: 12px 16px;
      border-bottom: 1px solid var(--color-border);
      box-shadow: var(--shadow-lg);
      display: flex;
      align-items: center;
      gap: 12px;
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

    .add-evidence-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border: 1px solid var(--color-accent);
      border-radius: var(--radius-sm);
      background: var(--color-accent);
      color: white;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s, box-shadow 0.15s;
    }

    .add-evidence-btn:hover {
      opacity: 0.9;
      box-shadow: var(--shadow-sm);
    }

    .detail-body {
      width: 92%;
      max-width: 960px;
      height: 75vh;
      background: var(--color-surface);
      border-radius: 0 0 var(--radius-lg) var(--radius-lg);
      box-shadow: var(--shadow-lg);
      overflow-y: auto;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .detail-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .detail-field label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
    }

    .detail-query {
      padding: 10px 12px;
      background: var(--color-bg);
      border-radius: var(--radius-sm);
      font-family: var(--font-mono, monospace);
      font-size: 0.8125rem;
      line-height: 1.5;
      white-space: pre-wrap;
      margin: 0;
    }

    .detail-explanation {
      font-size: 0.875rem;
      color: var(--color-text);
      margin: 0;
      line-height: 1.5;
    }

    .table-scroll {
      overflow: auto;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      flex: 1;
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

    .col-check {
      width: 36px;
      text-align: center;
      vertical-align: middle;
    }

    .check-wrap {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      cursor: pointer;
    }

    .check-wrap input {
      position: absolute;
      opacity: 0;
      width: 0;
      height: 0;
    }

    .checkmark {
      width: 16px;
      height: 16px;
      border: 1.5px solid var(--color-border);
      border-radius: 3px;
      background: var(--color-surface);
      transition: border-color 0.15s, background 0.15s;
    }

    .check-wrap input:checked + .checkmark {
      background: var(--color-accent);
      border-color: var(--color-accent);
    }

    .check-wrap input:checked + .checkmark::after {
      content: '';
      display: block;
      width: 4px;
      height: 8px;
      border: solid white;
      border-width: 0 2px 2px 0;
      transform: rotate(45deg);
      margin: 1px auto 0;
    }

    .check-wrap:hover .checkmark {
      border-color: var(--color-accent);
    }

    tr.row-selected td {
      background: var(--color-accent-subtle);
    }

    .evidence-form {
      background: var(--color-bg);
      border: 1px solid var(--color-accent);
      border-radius: var(--radius-sm);
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .evidence-form label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text);
    }

    .evidence-textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      color: var(--color-text);
      font-size: 0.8125rem;
      font-family: inherit;
      line-height: 1.5;
      resize: vertical;
      transition: border-color 0.15s;
      box-sizing: border-box;
    }

    .evidence-textarea:focus {
      outline: none;
      border-color: var(--color-accent);
    }

    .evidence-form-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .form-cancel {
      padding: 6px 14px;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: var(--color-surface);
      color: var(--color-text);
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.15s;
    }

    .form-cancel:hover {
      border-color: var(--color-border-focus);
    }

    .form-confirm {
      padding: 6px 14px;
      border: 1px solid var(--color-accent);
      border-radius: var(--radius-sm);
      background: var(--color-accent);
      color: white;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s;
    }

    .form-confirm:hover {
      opacity: 0.9;
    }

    .form-confirm:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .header-actions {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }

    .action-btn {
      display: inline-flex;
      align-items: center;
      padding: 6px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s, box-shadow 0.15s, border-color 0.15s;
    }

    .action-approve {
      border: 1px solid #22c55e;
      background: #22c55e;
      color: white;
    }

    .action-approve:hover {
      opacity: 0.9;
      box-shadow: var(--shadow-sm);
    }

    .action-disabled {
      background: var(--color-border);
      border-color: var(--color-border);
      color: var(--color-text-secondary);
      cursor: not-allowed;
      opacity: 0.7;
    }

    .action-correct {
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-text);
    }

    .action-correct:hover {
      border-color: var(--color-accent);
      color: var(--color-accent);
    }

    .action-reject {
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-text-secondary);
    }

    .action-reject:hover {
      border-color: var(--color-error);
      color: var(--color-error);
    }

    .action-correct-cancel {
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-text);
    }

    .action-correct-cancel:hover {
      border-color: var(--color-border-focus);
    }

    .action-correct-save {
      border: 1px solid var(--color-accent);
      background: var(--color-accent);
      color: white;
    }

    .action-correct-save:hover {
      opacity: 0.9;
    }

    .action-correct-save:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .evidence-content-box {
      padding: 12px 14px;
      background: var(--color-bg);
      border-radius: var(--radius-sm);
    }

    .evidence-content-ai {
      border-left: 3px solid var(--color-warning);
      background: var(--color-warning-bg);
    }

    .chart-container {
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 12px;
      background: var(--color-bg);
      min-height: 300px;
    }

    .ai-badge-inline {
      display: inline-block;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--color-warning);
      background: rgba(217, 119, 6, 0.1);
      padding: 2px 8px;
      border-radius: 3px;
      margin-top: 8px;
    }
  `,
})
export class Workbench implements OnInit, OnDestroy {
  private chartContainerEl?: ElementRef<HTMLDivElement>;
  @ViewChild('chartContainer') set chartContainer(el: ElementRef<HTMLDivElement> | undefined) {
    this.chartContainerEl = el;
    if (el && this.viewingDetail?.chart_spec) {
      this.renderSelectableChart(el.nativeElement, this.viewingDetail.chart_spec, this.viewingDetail.result, this.selectedRows);
    }
  }

  private evidenceChartContainerEl?: ElementRef<HTMLDivElement>;
  @ViewChild('evidenceChartContainer') set evidenceChartContainer(el: ElementRef<HTMLDivElement> | undefined) {
    this.evidenceChartContainerEl = el;
    if (el && this.evidenceSourceShoebox?.chart_spec) {
      this.renderLockedChart(el.nativeElement, this.evidenceSourceShoebox.chart_spec, this.evidenceSourceShoebox.result, this.evidenceSelectedRows);
    }
  }

  workspaceId = '';
  sourcesOpen = false;
  shoeboxItems: ShoeboxItemSummary[] = [];
  viewingDetail: ShoeboxItemFull | null = null;
  detailColumns: string[] = [];
  selectedRows = new Set<number>();
  private brushing = false;
  addingEvidence = false;
  evidenceText = '';

  evidenceItems: EvidenceItemSummary[] = [];
  viewingEvidence: EvidenceItemFull | null = null;
  evidenceSourceShoebox: ShoeboxItemFull | null = null;
  evidenceSelectedRows = new Set<number>();
  evidenceSourceColumns: string[] = [];
  verifyCountdown = 0;
  correctingEvidence = false;
  correctText = '';
  private verifyTimer: ReturnType<typeof setInterval> | null = null;

  schemaData: SchematizationData = { frames: [], evidence: [], relationships: [] };
  schemaEvidence: EvidenceItemSummary[] = [];
  schemaDragover = false;

  newShoeboxIds = new Set<string>();
  unseenShoeboxIds = new Set<string>();
  aiCooking = false;
  private knownShoeboxIds = new Set<string>();
  private shoeboxInitialLoad = true;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private cookingTimeout: ReturnType<typeof setTimeout> | null = null;

  newEvidenceIds = new Set<string>();
  unseenEvidenceIds = new Set<string>();
  evidenceCooking = false;
  private knownEvidenceIds = new Set<string>();
  private evidenceInitialLoad = true;
  private evidencePollTimer: ReturnType<typeof setInterval> | null = null;
  private evidenceCookingTimeout: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private route: ActivatedRoute,
    private shoeboxSvc: ShoeboxService,
    private evidenceSvc: EvidenceService,
    private schemaSvc: SchematizationService,
  ) {}

  ngOnInit(): void {
    this.workspaceId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadShoebox();
    this.loadEvidence();
    this.loadSchematization();
    this.pollTimer = setInterval(() => this.loadShoebox(), 5000);
    this.evidencePollTimer = setInterval(() => this.loadEvidence(), 5000);
  }

  ngOnDestroy(): void {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.cookingTimeout !== null) {
      clearTimeout(this.cookingTimeout);
      this.cookingTimeout = null;
    }
    if (this.evidencePollTimer !== null) {
      clearInterval(this.evidencePollTimer);
      this.evidencePollTimer = null;
    }
    if (this.evidenceCookingTimeout !== null) {
      clearTimeout(this.evidenceCookingTimeout);
      this.evidenceCookingTimeout = null;
    }
    this.clearVerifyTimer();
  }

  viewItem(item: ShoeboxItemSummary): void {
    this.unseenShoeboxIds.delete(item.id);
    this.unseenShoeboxIds = new Set(this.unseenShoeboxIds);
    this.shoeboxSvc.get(this.workspaceId, item.id).subscribe((full) => {
      this.viewingDetail = full;
      this.detailColumns =
        full.result.length > 0 ? Object.keys(full.result[0]) : [];
      this.selectedRows = new Set();
      this.addingEvidence = false;
      this.evidenceText = '';
    });
  }

  private renderSelectableChart(
    el: HTMLDivElement,
    spec: Record<string, any>,
    data: Record<string, any>[],
    selectedRows: Set<number>,
  ): void {
    const stamped = data.map((row, i) => ({ ...row, _vi: i } as Record<string, any>));
    const containerWidth = el.clientWidth - 24;
    const fullSpec = {
      ...spec,
      width: Math.max(containerWidth, 200),
      autosize: { type: 'fit', contains: 'padding' },
      data: { values: stamped },
    } as VisualizationSpec;
    embed(el, fullSpec, { actions: false, renderer: 'svg' }).then(({ view }) => {
      view.addSignalListener('brush', (_name, value) => {
        if (!value || !this.viewingDetail) return;
        const fields = Object.keys(value);
        if (fields.length === 0) return;
        const brushed = new Set<number>();
        for (let i = 0; i < stamped.length; i++) {
          let inside = true;
          for (const field of fields) {
            const range = value[field];
            if (!Array.isArray(range) || range.length !== 2) { inside = false; break; }
            const v = stamped[i][field];
            if (v == null) { inside = false; break; }
            const numV = typeof v === 'string' ? new Date(v).getTime() : Number(v);
            const lo = typeof range[0] === 'string' ? new Date(range[0]).getTime() : Number(range[0]);
            const hi = typeof range[1] === 'string' ? new Date(range[1]).getTime() : Number(range[1]);
            if (numV < Math.min(lo, hi) || numV > Math.max(lo, hi)) { inside = false; break; }
          }
          if (inside) brushed.add(i);
        }
        const merged = new Set(this.selectedRows);
        for (const idx of brushed) merged.add(idx);
        this.selectedRows = merged;
      });
    }).catch(() => {});
  }

  private renderLockedChart(
    el: HTMLDivElement,
    spec: Record<string, any>,
    data: Record<string, any>[],
    selectedRows: Set<number>,
  ): void {
    const stamped = data.map((row, i) => ({ ...row, _selected: selectedRows.has(i) }));
    const containerWidth = el.clientWidth - 24;
    const { params: _dropped, ...specNoParams } = spec;
    const fullSpec = {
      ...specNoParams,
      width: Math.max(containerWidth, 200),
      autosize: { type: 'fit', contains: 'padding' },
      data: { values: stamped },
      encoding: {
        ...(specNoParams['encoding'] || {}),
        opacity: {
          condition: { test: 'datum._selected', value: 1 },
          value: 0.2,
        },
      },
    } as VisualizationSpec;
    embed(el, fullSpec, { actions: false, renderer: 'svg' }).catch(() => {});
  }

  closeDetail(): void {
    this.viewingDetail = null;
    this.selectedRows = new Set();
    this.addingEvidence = false;
    this.evidenceText = '';
  }

  triggerAiSearch(): void {
    this.schemaSvc.triggerAiSearch(this.workspaceId).subscribe(() => {
      this.startCooking();
    });
  }

  loadShoebox(): void {
    this.shoeboxSvc.list(this.workspaceId).subscribe((items) => {
      if (this.shoeboxInitialLoad) {
        this.shoeboxItems = items;
        this.knownShoeboxIds = new Set(items.map((i) => i.id));
        this.shoeboxInitialLoad = false;
        return;
      }
      const freshAiIds: string[] = [];
      for (const item of items) {
        if (!this.knownShoeboxIds.has(item.id) && item.ai_authored) {
          freshAiIds.push(item.id);
        }
      }
      this.shoeboxItems = items;
      this.knownShoeboxIds = new Set(items.map((i) => i.id));
      if (freshAiIds.length > 0) {
        this.stopCooking();
        this.startEvidenceCooking();
        for (const id of freshAiIds) {
          this.newShoeboxIds.add(id);
          this.unseenShoeboxIds.add(id);
        }
        this.newShoeboxIds = new Set(this.newShoeboxIds);
        this.unseenShoeboxIds = new Set(this.unseenShoeboxIds);
        setTimeout(() => {
          for (const id of freshAiIds) {
            this.newShoeboxIds.delete(id);
          }
          this.newShoeboxIds = new Set(this.newShoeboxIds);
        }, 2500);
      }
    });
  }

  removeFromShoebox(event: Event, item: ShoeboxItemSummary): void {
    event.stopPropagation();
    this.shoeboxSvc.remove(this.workspaceId, item.id).subscribe(() => {
      this.shoeboxItems = this.shoeboxItems.filter((i) => i.id !== item.id);
    });
  }

  toggleRow(index: number): void {
    if (this.selectedRows.has(index)) {
      this.selectedRows.delete(index);
    } else {
      this.selectedRows.add(index);
    }
    this.selectedRows = new Set(this.selectedRows);
  }

  toggleAllRows(): void {
    if (!this.viewingDetail) return;
    if (this.allRowsSelected()) {
      this.selectedRows = new Set();
    } else {
      this.selectedRows = new Set(
        this.viewingDetail.result.map((_, i) => i)
      );
    }
  }

  allRowsSelected(): boolean {
    if (!this.viewingDetail || this.viewingDetail.result.length === 0) return false;
    return this.selectedRows.size === this.viewingDetail.result.length;
  }

  confirmAddEvidence(): void {
    if (!this.viewingDetail || !this.evidenceText.trim()) return;
    const rows = Array.from(this.selectedRows).sort((a, b) => a - b);
    this.evidenceSvc
      .add(this.workspaceId, this.viewingDetail.id, this.evidenceText.trim(), rows)
      .subscribe(() => {
        this.addingEvidence = false;
        this.evidenceText = '';
        this.selectedRows = new Set();
        this.loadEvidence();
      });
  }

  loadEvidence(): void {
    this.evidenceSvc.list(this.workspaceId).subscribe((items) => {
      if (this.evidenceInitialLoad) {
        this.evidenceItems = items;
        this.knownEvidenceIds = new Set(items.map((i) => i.id));
        this.evidenceInitialLoad = false;
        this.updateFilteredEvidence();
        return;
      }
      const freshAiIds: string[] = [];
      for (const item of items) {
        if (!this.knownEvidenceIds.has(item.id) && item.ai_authored) {
          freshAiIds.push(item.id);
        }
      }
      this.evidenceItems = items;
      this.knownEvidenceIds = new Set(items.map((i) => i.id));
      this.updateFilteredEvidence();
      if (freshAiIds.length > 0) {
        this.stopEvidenceCooking();
        for (const id of freshAiIds) {
          this.newEvidenceIds.add(id);
          this.unseenEvidenceIds.add(id);
        }
        this.newEvidenceIds = new Set(this.newEvidenceIds);
        this.unseenEvidenceIds = new Set(this.unseenEvidenceIds);
        setTimeout(() => {
          for (const id of freshAiIds) {
            this.newEvidenceIds.delete(id);
          }
          this.newEvidenceIds = new Set(this.newEvidenceIds);
        }, 2500);
      }
    });
  }

  loadSchematization(): void {
    this.schemaSvc.get(this.workspaceId).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
    });
  }

  get filteredEvidence(): EvidenceItemSummary[] {
    const schemaIds = new Set(this.schemaData.evidence);
    return this.evidenceItems.filter((item) => !schemaIds.has(item.id));
  }

  private updateFilteredEvidence(): void {
    const schemaIds = new Set(this.schemaData.evidence);
    this.schemaEvidence = this.evidenceItems.filter((item) => schemaIds.has(item.id));
  }

  isDraggable(item: EvidenceItemSummary): boolean {
    return !this.isUncertain(item);
  }

  onDragStart(event: DragEvent, item: EvidenceItemSummary): void {
    event.dataTransfer?.setData('text/plain', item.id);
  }

  onSchemaDragover(event: DragEvent): void {
    event.preventDefault();
    this.schemaDragover = true;
  }

  onSchemaDragleave(event: DragEvent): void {
    const target = event.currentTarget as HTMLElement;
    const related = event.relatedTarget as Node | null;
    if (related && target.contains(related)) return;
    this.schemaDragover = false;
  }

  onSchemaDrop(event: DragEvent): void {
    event.preventDefault();
    this.schemaDragover = false;
    const evidenceId = event.dataTransfer?.getData('text/plain');
    if (!evidenceId) return;
    this.schemaSvc.addEvidence(this.workspaceId, evidenceId).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
      this.startCooking();
      this.startEvidenceCooking();
    });
  }

  removeFromSchema(event: Event, item: EvidenceItemSummary): void {
    event.stopPropagation();
    this.schemaSvc.removeEvidence(this.workspaceId, item.id).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
      if (resp.data.evidence.length > 0) {
        this.startCooking();
        this.startEvidenceCooking();
      } else {
        this.stopCooking();
        this.stopEvidenceCooking();
      }
    });
  }

  private startCooking(): void {
    this.aiCooking = true;
    if (this.cookingTimeout !== null) {
      clearTimeout(this.cookingTimeout);
    }
    this.cookingTimeout = setTimeout(() => {
      this.aiCooking = false;
      this.cookingTimeout = null;
    }, 30000);
  }

  private stopCooking(): void {
    this.aiCooking = false;
    if (this.cookingTimeout !== null) {
      clearTimeout(this.cookingTimeout);
      this.cookingTimeout = null;
    }
  }

  private startEvidenceCooking(): void {
    this.evidenceCooking = true;
    if (this.evidenceCookingTimeout !== null) {
      clearTimeout(this.evidenceCookingTimeout);
    }
    this.evidenceCookingTimeout = setTimeout(() => {
      this.evidenceCooking = false;
      this.evidenceCookingTimeout = null;
    }, 30000);
  }

  private stopEvidenceCooking(): void {
    this.evidenceCooking = false;
    if (this.evidenceCookingTimeout !== null) {
      clearTimeout(this.evidenceCookingTimeout);
      this.evidenceCookingTimeout = null;
    }
  }

  isUncertain(item: { ai_authored: boolean; approved: boolean }): boolean {
    return item.ai_authored && !item.approved;
  }

  viewEvidenceItem(item: EvidenceItemSummary): void {
    this.unseenEvidenceIds.delete(item.id);
    this.unseenEvidenceIds = new Set(this.unseenEvidenceIds);
    this.evidenceSvc.get(this.workspaceId, item.id).subscribe((full) => {
      this.viewingEvidence = full;
      this.correctingEvidence = false;
      this.correctText = '';
      this.startVerifyCountdown(this.isUncertain(full));
      this.shoeboxSvc.get(this.workspaceId, full.shoebox_id).subscribe((shoebox) => {
        this.evidenceSourceExplanation = shoebox.explanation;
        this.evidenceSourceData = full.rows.map((i) => shoebox.result[i]).filter(Boolean);
        this.evidenceSourceColumns =
          this.evidenceSourceData.length > 0
            ? Object.keys(this.evidenceSourceData[0])
            : [];
      });
    });
  }

  closeEvidenceDetail(): void {
    this.viewingEvidence = null;
    this.evidenceSourceExplanation = '';
    this.correctingEvidence = false;
    this.correctText = '';
    this.clearVerifyTimer();
  }

  approveEvidence(): void {
    if (!this.viewingEvidence) return;
    this.evidenceSvc.approve(this.workspaceId, this.viewingEvidence.id).subscribe(() => {
      this.closeEvidenceDetail();
      this.loadEvidence();
    });
  }

  rejectEvidence(): void {
    if (!this.viewingEvidence) return;
    this.evidenceSvc.reject(this.workspaceId, this.viewingEvidence.id).subscribe(() => {
      this.closeEvidenceDetail();
      this.loadEvidence();
    });
  }

  startCorrecting(): void {
    if (!this.viewingEvidence) return;
    this.correctingEvidence = true;
    this.correctText = this.viewingEvidence.content;
  }

  cancelCorrecting(): void {
    this.correctingEvidence = false;
    this.correctText = '';
  }

  saveCorrectedEvidence(): void {
    if (!this.viewingEvidence || !this.correctText.trim()) return;
    this.evidenceSvc
      .correct(this.workspaceId, this.viewingEvidence.id, this.correctText.trim())
      .subscribe(() => {
        this.closeEvidenceDetail();
        this.loadEvidence();
      });
  }

  private startVerifyCountdown(uncertain: boolean): void {
    this.clearVerifyTimer();
    if (!uncertain) {
      this.verifyCountdown = 0;
      return;
    }
    this.verifyCountdown = 10;
    this.verifyTimer = setInterval(() => {
      this.verifyCountdown--;
      if (this.verifyCountdown <= 0) {
        this.clearVerifyTimer();
      }
    }, 1000);
  }

  private clearVerifyTimer(): void {
    if (this.verifyTimer !== null) {
      clearInterval(this.verifyTimer);
      this.verifyTimer = null;
    }
  }

  removeEvidence(event: Event, item: EvidenceItemSummary): void {
    event.stopPropagation();
    this.evidenceSvc.remove(this.workspaceId, item.id).subscribe(() => {
      this.evidenceItems = this.evidenceItems.filter((i) => i.id !== item.id);
    });
  }
}
