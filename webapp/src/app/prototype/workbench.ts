import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
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
  SchemaNode,
  RelType,
  allEvidenceIds,
} from './schematization.service';
import { maxOverlap } from './text-overlap';

interface ResolvedNode {
  type: 'evidence' | 'frame';
  id: string;
  rel?: RelType;
  suggestion?: boolean;
  evidence?: EvidenceItemSummary;
  title?: string;
  description?: string;
  children: ResolvedNode[];
}

interface DropIndicator {
  parentId: string | null;
  index: number;
}

@Component({
  selector: 'app-workbench',
  imports: [SourcesModal, FormsModule, NgTemplateOutlet],
  template: `
    <div class="workbench">
      <div class="workbench-board">
        <section class="board-column">
          <h2>
            Resultados
            <button class="ai-search-btn"
                    [class.ai-search-cooking]="aiSearchRunning"
                    [disabled]="aiSearchRunning"
                    (click)="triggerAiSearch()"
                    title="Busca IA">
              <svg class="sparkle-icon" width="14" height="14" viewBox="0 0 24 24"
                   fill="currentColor" stroke="none">
                <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
              </svg>
            </button>
          </h2>
          @if (aiSearchRunning) {
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
            @if (sortedShoebox.length === 0) {
              <p class="placeholder">Nenhum resultado adicionado</p>
            }
            @for (item of sortedShoebox; track item.id) {
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
                    <svg width="20" height="20" viewBox="0 0 24 24"
                         fill="currentColor" stroke="none">
                      <path d="M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm-8 18v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2z"/>
                    </svg>
                  }
                </div>
                <div class="card-info">
                  <span class="card-name" [title]="item.explanation">{{ item.explanation }}</span>
                  @if (shoeboxScores.get(item.id); as score) {
                    <span class="overlap-tag">{{ Math.round(score * 100) }}% pertinente</span>
                  }
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
          <h2>
            Evidências
            <button class="ai-search-btn"
                    [class.ai-search-cooking]="aiExtractRunning"
                    [disabled]="aiExtractRunning || shoeboxItems.length === 0"
                    (click)="triggerAiExtract()"
                    title="Extrair evidências IA">
              <svg class="sparkle-icon" width="14" height="14" viewBox="0 0 24 24"
                   fill="currentColor" stroke="none">
                <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
              </svg>
            </button>
          </h2>
          @if (aiExtractRunning) {
            <div class="ai-shimmer"></div>
          }
          <div class="column-body">
            @if (sortedEvidence.length === 0) {
              <p class="placeholder">Nenhuma evidência extraída</p>
            }
            @for (item of sortedEvidence; track item.id) {
              <div
                class="evidence-card"
                [class.evidence-ai]="isUncertain(item)"
                [class.evidence-card-new]="newEvidenceIds.has(item.id)"
                [draggable]="true"
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
                         [attr.fill]="isUncertain(item) ? 'var(--color-warning)' : '#16a34a'"
                         stroke="none">
                      <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
                    </svg>
                  } @else {
                    <svg width="20" height="20" viewBox="0 0 24 24"
                         fill="currentColor" stroke="none">
                      <path d="M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm-8 18v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2z"/>
                    </svg>
                  }
                </div>
                <div class="card-info">
                  <span class="card-name" [title]="item.content">{{ item.content }}</span>
                  @if (evidenceScores.get(item.id); as score) {
                    <span class="overlap-tag">{{ Math.round(score * 100) }}% pertinente</span>
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
          (dragover)="onSchemaDragover($event)"
          (dragleave)="onSchemaDragleave($event)"
          (drop)="onSchemaDrop($event)"
        >
          <h2>
            Esquematização
            <button class="ai-search-btn"
                    [class.ai-search-cooking]="aiBuildCaseRunning"
                    [disabled]="aiBuildCaseRunning || evidenceItems.length === 0 || knownSuggestionIds.size >= 5"
                    (click)="triggerAiBuildCase()"
                    title="Sugerir esquematização IA">
              <svg class="sparkle-icon" width="14" height="14" viewBox="0 0 24 24"
                   fill="currentColor" stroke="none">
                <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
              </svg>
            </button>
          </h2>
          @if (aiBuildCaseRunning) {
            <div class="ai-shimmer"></div>
          }
          <div class="column-body schema-drop-zone" data-node-id="root">

            <ng-template #schemaNodeTpl let-node>
              @if (node.type === 'evidence' && node.evidence) {
                <div class="schema-node schema-node-evidence"
                     [class.schema-node-cancelled]="isCancelled(node)"
                     [class.schema-node-suggestion]="node.suggestion"
                     [draggable]="!node.suggestion"
                     (dragstart)="onSchemaDragStart($event, node)"
                     [attr.data-node-id]="node.id"
                     (click)="onEvidenceNodeClick($event, node.evidence, node)">
                  <div class="evidence-row">
                    @if (node.rel) {
                      <button class="rel-tag"
                              [class.rel-tag-cancel]="node.rel === 'cancel'"
                              [class.rel-tag-question]="node.rel === 'question'"
                              [class.rel-tag-elaborate]="node.rel === 'elaborate'"
                              (click)="cycleRel($event, node)"
                              [title]="relLabel(node.rel)"
                              [disabled]="node.suggestion">
                        {{ relIcon(node.rel) }}
                      </button>
                    }
                    <div class="card-info">
                      <span class="card-name" [title]="node.evidence.content">{{ node.evidence.content }}</span>
                    </div>
                    <button class="card-remove" (click)="removeSchemaNode($event, node)" aria-label="Remover">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2.5"
                           stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                  @if (node.children.length > 0 || dropIndicator?.parentId === node.id) {
                    <div class="evidence-children" [attr.data-node-id]="node.id">
                      @if (dropIndicator?.parentId === node.id && dropIndicator?.index === 0) {
                        <div class="drop-line"></div>
                      }
                      @for (child of node.children; track child.id; let ci = $index) {
                        <ng-container *ngTemplateOutlet="schemaNodeTpl; context: { $implicit: child }"></ng-container>
                        @if (dropIndicator?.parentId === node.id && dropIndicator?.index === ci + 1) {
                          <div class="drop-line"></div>
                        }
                      }
                    </div>
                  }
                </div>
              }
              @if (node.type === 'frame') {
                <div class="schema-node schema-node-frame"
                     [class.schema-node-cancelled]="isCancelled(node)"
                     [draggable]="true"
                     (dragstart)="onSchemaDragStart($event, node)"
                     [attr.data-node-id]="node.id">
                  <div class="frame-header">
                    @if (node.rel) {
                      <button class="rel-tag"
                              [class.rel-tag-cancel]="node.rel === 'cancel'"
                              [class.rel-tag-question]="node.rel === 'question'"
                              [class.rel-tag-elaborate]="node.rel === 'elaborate'"
                              (click)="cycleRel($event, node)"
                              [title]="relLabel(node.rel)">
                        {{ relIcon(node.rel) }}
                      </button>
                    }
                    @if (editingFrameId === node.id) {
                      <input class="frame-title-input"
                             [value]="node.title"
                             (blur)="saveFrameTitle($event, node.id)"
                             (keydown.enter)="$any($event.target).blur()"
                             #frameTitleInput />
                    } @else {
                      <span class="frame-title" [class.frame-title-empty]="!node.title" (click)="startEditingFrame(node.id)">
                        {{ node.title || 'Adicione um título...' }}
                        <svg class="pen-icon" width="10" height="10" viewBox="0 0 24 24" fill="none"
                             stroke="currentColor" stroke-width="2"
                             stroke-linecap="round" stroke-linejoin="round">
                          <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                        </svg>
                      </span>
                    }
                    <button class="card-remove" (click)="removeSchemaNode($event, node)" aria-label="Remover">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2.5"
                           stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                  @if (editingDescId === node.id) {
                    <textarea class="frame-desc-input"
                              [value]="node.description || ''"
                              (blur)="saveFrameDesc($event, node.id)"
                              (keydown.enter)="$any($event.target).blur()"
                              rows="2"
                              #frameDescInput></textarea>
                  } @else {
                    <p class="frame-description" [class.frame-description-empty]="!node.description" (click)="startEditingDesc(node.id)">
                      {{ node.description || 'Descreva esta hipótese...' }}
                      <svg class="pen-icon" width="10" height="10" viewBox="0 0 24 24" fill="none"
                           stroke="currentColor" stroke-width="2"
                           stroke-linecap="round" stroke-linejoin="round">
                        <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                      </svg>
                    </p>
                  }
                  <div class="frame-children" [attr.data-node-id]="node.id">
                    <p class="frame-placeholder">Arraste evidências</p>
                    @if (dropIndicator?.parentId === node.id && dropIndicator?.index === 0) {
                      <div class="drop-line"></div>
                    }
                    @for (child of node.children; track child.id; let ci = $index) {
                      <ng-container *ngTemplateOutlet="schemaNodeTpl; context: { $implicit: child }"></ng-container>
                      @if (dropIndicator?.parentId === node.id && dropIndicator?.index === ci + 1) {
                        <div class="drop-line"></div>
                      }
                    }
                  </div>
                </div>
              }
            </ng-template>

            <p class="frame-placeholder"><a class="frame-link" (click)="createNewFrame()">Crie hipóteses</a> e arraste evidências a elas</p>
            @if (dropIndicator?.parentId === null && dropIndicator?.index === 0) {
              <div class="drop-line"></div>
            }
            @for (node of schemaResolvedItems; track node.id; let i = $index) {
              <ng-container *ngTemplateOutlet="schemaNodeTpl; context: { $implicit: node }"></ng-container>
              @if (dropIndicator?.parentId === null && dropIndicator?.index === i + 1) {
                <div class="drop-line"></div>
              }
            }
          </div>
          <button class="fab" (click)="createNewFrame()" title="Nova Hipótese">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.5"
                 stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
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
        <div class="detail-panel">
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
          </header>
          <div class="detail-body">
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
                      <tr [class.row-selected]="selectedRows.has($index)"
                          [class.row-dimmed]="selectedRows.size > 0 && !selectedRows.has($index)">
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
          <div class="detail-footer">
            @if (addingEvidence) {
              <div class="footer-form">
                <textarea
                  class="evidence-textarea"
                  [(ngModel)]="evidenceText"
                  rows="2"
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
            } @else {
              <span class="footer-hint" [class.footer-hint-hidden]="selectedRows.size > 0">selecione dados para criar evidência</span>
              <div class="footer-actions">
                @if (selectedRows.size > 0) {
                  <button class="chart-action-btn chart-clear-btn" (click)="clearSelection()">
                    Limpar seleção
                  </button>
                }
                <button
                  class="add-evidence-btn"
                  [disabled]="selectedRows.size === 0"
                  (click)="addingEvidence = true"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" stroke-width="2"
                       stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Adicionar Evidência
                </button>
              </div>
            }
          </div>
        </div>
      </div>
    }
    @if (viewingEvidence) {
      <div class="detail-backdrop" (click)="closeEvidenceDetail()"></div>
      <div class="detail-modal">
        <div class="detail-panel">
          <div class="detail-body">
            <div class="detail-field">
              <label>Evidência</label>
              <div class="evidence-content-box" [class.evidence-content-ai]="isUncertain(viewingEvidence)">
                <p class="detail-explanation">{{ viewingEvidence.content }}</p>
              </div>
            </div>
            @if (evidenceSourceShoebox?.query) {
              <div class="detail-field">
                <label>Consulta</label>
                <pre class="detail-query">{{ evidenceSourceShoebox!.query }}</pre>
              </div>
            }
            @if (evidenceSourceShoebox?.chart_spec) {
              <div class="detail-field">
                <label>Visualização</label>
                <div class="chart-container" #evidenceChartContainer></div>
              </div>
            }
            @if (evidenceSourceExplanation) {
              <div class="detail-field">
                <label>Explicação do Resultado</label>
                <p class="detail-explanation">{{ evidenceSourceExplanation }}</p>
              </div>
            }
            @if (evidenceSourceData.length > 0) {
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
          @if (isUncertain(viewingEvidence) || viewingSuggestionNodeId) {
            <div class="detail-footer">
              @if (correctingEvidence) {
                <div class="footer-form">
                  <textarea
                    class="evidence-textarea"
                    [(ngModel)]="correctText"
                    rows="3"
                  ></textarea>
                  <div class="evidence-form-actions">
                    <button class="form-cancel" (click)="cancelCorrecting()">
                      Cancelar
                    </button>
                    <button
                      class="form-confirm"
                      [disabled]="!correctText.trim()"
                      (click)="saveCorrectedEvidence()"
                    >
                      Salvar
                    </button>
                  </div>
                </div>
              } @else if (confirmingReject) {
                <span class="footer-hint">Se você rejeitar, essa evidência será removida da lista de evidências. Confirmar?</span>
                <div class="footer-actions">
                  <button class="action-btn action-correct" (click)="confirmingReject = false">
                    Cancelar
                  </button>
                  <button class="action-btn action-reject-confirm" (click)="rejectEvidence()">
                    Confirmar rejeição
                  </button>
                </div>
              } @else {
                <span class="footer-hint" [class.footer-hint-hidden]="verifyCountdown === 0">A IA pode cometer erros, verifique se a evidência condiz com os dados antes de aprovar</span>
                <div class="footer-actions">
                  <button class="action-btn action-correct" (click)="closeEvidenceDetail()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="2"
                         stroke-linecap="round" stroke-linejoin="round">
                      <line x1="19" y1="12" x2="5" y2="12"/>
                      <polyline points="12 19 5 12 12 5"/>
                    </svg>
                    Voltar
                  </button>
                  <button class="action-btn action-reject" (click)="confirmingReject = true">
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

    .workbench-board {
      display: flex;
      flex: 1;
      overflow-x: auto;
    }

    .board-column {
      width: 20%;
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

    .schema-drop-zone {
      position: relative;
    }

    .schema-node {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 10px;
      background: var(--color-frame-bg, #F3F0FF);
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: box-shadow 0.15s, transform 0.15s;
      position: relative;
    }

    .schema-node:hover {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
      transform: translateY(-1px);
    }

    .schema-node-evidence {
      background: var(--color-surface);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      flex-direction: column;
      gap: 6px;
    }

    .evidence-row {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      width: 100%;
    }

    .evidence-children {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding-left: 12px;
      border-left: 2px solid var(--color-border);
      margin-top: 4px;
      min-height: 8px;
    }

    .schema-node-frame > .frame-header .card-name {
      font-family: inherit;
      color: var(--color-frame-text, #6D28D9);
    }

    .schema-node-frame {
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .schema-node .card-remove {
      opacity: 0;
    }

    .schema-node:hover .card-remove {
      opacity: 1;
    }

    .schema-node-frame {
      flex-direction: column;
      gap: 6px;
      padding: 10px;
      border-radius: var(--radius-md);
    }

    .frame-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
    }

    .frame-title {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--color-frame-text, #6D28D9);
      cursor: text;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .frame-title .pen-icon {
      opacity: 0;
      color: var(--color-text-secondary);
      transition: opacity 0.15s;
    }

    .frame-title:hover .pen-icon {
      opacity: 0.7;
    }

    .frame-title-input {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--color-frame-text, #6D28D9);
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--color-frame-text, #6D28D9);
      outline: none;
      padding: 0;
      font-family: inherit;
      width: 100%;
      min-width: 0;
      flex: 1;
    }

    .frame-description {
      font-size: 0.75rem;
      color: var(--color-text-secondary);
      margin: 0;
      cursor: text;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .frame-description .pen-icon {
      opacity: 0;
      color: var(--color-text-secondary);
      transition: opacity 0.15s;
    }

    .frame-description:hover .pen-icon {
      opacity: 0.7;
    }

    .frame-title-empty {
      font-style: italic;
      font-weight: 400;
      opacity: 0.6;
    }

    .frame-description-empty {
      font-style: italic;
      opacity: 0.6;
    }

    .frame-desc-input {
      font-size: 0.75rem;
      color: var(--color-text-secondary);
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--color-frame-text, #6D28D9);
      outline: none;
      padding: 0;
      font-family: inherit;
      resize: none;
      width: 100%;
      line-height: 1.4;
    }

    .frame-children {
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-height: 28px;
      margin-top: 4px;
      position: relative;
    }

    .frame-placeholder {
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--color-text-secondary);
      opacity: 0.5;
      padding: 2px 0;
      margin: 0;
    }

    .frame-link {
      color: var(--color-frame-text, #6D28D9);
      cursor: pointer;
      text-decoration: underline;
      opacity: 1;
    }

    .frame-link:hover {
      opacity: 0.8;
    }

    .drop-line {
      height: 2px;
      background: var(--color-accent);
      border-radius: 1px;
      flex-shrink: 0;
    }

    .rel-tag {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border: none;
      border-radius: 3px;
      color: white;
      font-size: 0.75rem;
      font-weight: 700;
      line-height: 1;
      cursor: pointer;
      flex-shrink: 0;
      padding: 0;
      transition: opacity 0.15s;
    }

    .rel-tag:hover {
      opacity: 0.8;
    }

    .rel-tag-elaborate {
      background: #16a34a;
    }

    .rel-tag-question {
      background: var(--color-warning);
    }

    .rel-tag-cancel {
      background: var(--color-error);
    }

    .schema-node-suggestion {
      background: var(--color-warning-bg, #FEF3C7);
      border: 2px dashed var(--color-warning, #D97706);
      cursor: default;
    }

    .schema-node-suggestion[draggable="false"] {
      cursor: default;
    }

    .schema-node-suggestion .rel-tag:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .schema-node-cancelled > .evidence-row,
    .schema-node-cancelled > .frame-header,
    .schema-node-cancelled > .frame-description {
      opacity: 0.45;
    }

    .schema-node-cancelled > .evidence-row .card-name,
    .schema-node-cancelled > .frame-header .frame-title {
      text-decoration: line-through;
    }

    .schema-column {
      position: relative;
    }

    .fab {
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      border: none;
      background: var(--color-frame-text, #6D28D9);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(109, 40, 217, 0.35);
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s;
      z-index: 10;
    }

    .fab:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 16px rgba(109, 40, 217, 0.45);
    }

    .fab:active {
      transform: scale(0.96);
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
      align-items: center;
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

    .shoebox-card {
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
      color: #16a34a;
    }

    .evidence-card-new {
      animation: card-fade-in 0.8s ease-out,
                 glow-fade 2.5s ease-out forwards;
    }

    .evidence-card {
      border-left: 3px solid #16a34a;
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
      pointer-events: none;
    }

    .detail-panel {
      pointer-events: auto;
      width: 92%;
      max-width: 960px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      overflow: hidden;
    }

    .detail-header {
      background: var(--color-surface);
      padding: 12px 16px;
      border-bottom: 1px solid var(--color-border);
      display: flex;
      align-items: center;
      gap: 12px;
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

    .add-evidence-btn:hover:not(:disabled) {
      opacity: 0.9;
      box-shadow: var(--shadow-sm);
    }

    .add-evidence-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .detail-footer {
      flex-shrink: 0;
      background: var(--color-surface);
      border-top: 1px solid var(--color-border);
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
    }

    .footer-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .footer-form {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .footer-form .evidence-form-actions {
      align-self: flex-end;
    }

    .footer-hint {
      font-size: 0.6875rem;
      color: var(--color-text-secondary);
    }

    .footer-hint-hidden {
      visibility: hidden;
    }

    .detail-body {
      flex: 1;
      min-height: 0;
      background: var(--color-surface);
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
      border: 1px solid #16a34a;
      background: #16a34a;
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

    .action-reject-confirm {
      border: 1px solid var(--color-error);
      background: var(--color-error);
      color: white;
    }

    .action-reject-confirm:hover {
      opacity: 0.9;
      box-shadow: var(--shadow-sm);
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

    .chart-actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }

    .chart-action-btn {
      padding: 5px 12px;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s, box-shadow 0.15s;
    }

    .chart-clear-btn {
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-text-secondary);
    }

    .chart-clear-btn:hover {
      border-color: var(--color-error);
      color: var(--color-error);
    }

    tr.row-dimmed td {
      opacity: 0.4;
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

    .overlap-tag {
      font-size: 0.625rem;
      color: var(--color-text-secondary);
      opacity: 0.7;
      margin-top: 2px;
      display: block;
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

  Math = Math;
  workspaceId = '';
  sourcesOpen = false;
  shoeboxItems: ShoeboxItemSummary[] = [];
  viewingDetail: ShoeboxItemFull | null = null;
  detailColumns: string[] = [];
  selectedRows = new Set<number>();
  addingEvidence = false;
  evidenceText = '';

  evidenceItems: EvidenceItemSummary[] = [];
  viewingEvidence: EvidenceItemFull | null = null;
  evidenceSourceShoebox: ShoeboxItemFull | null = null;
  evidenceSelectedRows = new Set<number>();
  evidenceSourceExplanation = '';
  evidenceSourceData: Record<string, any>[] = [];
  evidenceSourceColumns: string[] = [];
  verifyCountdown = 0;
  correctingEvidence = false;
  confirmingReject = false;
  correctText = '';
  private verifyTimer: ReturnType<typeof setInterval> | null = null;

  schemaData: SchematizationData = [];
  schemaResolvedItems: ResolvedNode[] = [];
  sortedShoebox: ShoeboxItemSummary[] = [];
  sortedEvidence: EvidenceItemSummary[] = [];
  shoeboxScores = new Map<string, number>();
  evidenceScores = new Map<string, number>();
  dropIndicator: DropIndicator | null = null;
  editingFrameId: string | null = null;
  editingDescId: string | null = null;
  private pendingDrop: { evidenceId: string; parentId?: string; index?: number } | null = null;
  viewingSuggestionNodeId: string | null = null;
  private dragoverRaf = false;

  newShoeboxIds = new Set<string>();
  unseenShoeboxIds = new Set<string>();
  aiSearchRunning = false;
  aiExtractRunning = false;
  aiBuildCaseRunning = false;
  private knownShoeboxIds = new Set<string>();
  private shoeboxInitialLoad = true;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  newEvidenceIds = new Set<string>();
  unseenEvidenceIds = new Set<string>();
  private knownEvidenceIds = new Set<string>();
  private evidenceInitialLoad = true;

  knownSuggestionIds = new Set<string>();

  constructor(
    private route: ActivatedRoute,
    private shoeboxSvc: ShoeboxService,
    private evidenceSvc: EvidenceService,
    private schemaSvc: SchematizationService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.workspaceId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadShoebox();
    this.loadEvidence();
    this.loadSchematization();
    this.pollTimer = setInterval(() => this.pollAll(), 1000);
  }

  ngOnDestroy(): void {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
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

  private markType(spec: Record<string, any>): string {
    return typeof spec['mark'] === 'string' ? spec['mark'] : spec['mark']?.type ?? '';
  }

  private isPathMark(spec: Record<string, any>): boolean {
    const m = this.markType(spec);
    return m === 'line' || m === 'trail';
  }

  private stampData(
    data: Record<string, any>[],
    selectedRows: Set<number>,
  ): Record<string, any>[] {
    return data.map((row, i) => ({
      ...row,
      _vi: i,
      _selected: selectedRows.has(i),
    }));
  }

  private buildSpec(
    spec: Record<string, any>,
    stamped: Record<string, any>[],
    selectedRows: Set<number>,
    containerWidth: number,
  ): Record<string, any> {
    const hasSelection = selectedRows.size > 0;
    const opacityEnc = hasSelection
      ? { condition: { test: 'datum._selected', value: 1 }, value: 0.3 }
      : undefined;
    const base = {
      width: Math.max(containerWidth, 200),
      autosize: { type: 'fit', contains: 'padding' },
      data: { values: stamped },
      title: spec['title'],
    } as Record<string, any>;

    if (this.isPathMark(spec)) {
      const enc = spec['encoding'] || {};
      const trailEnc = { x: enc['x'], y: enc['y'] } as Record<string, any>;
      const pointEnc = { x: enc['x'], y: enc['y'] } as Record<string, any>;
      if (enc['color']) {
        trailEnc['color'] = enc['color'];
        pointEnc['color'] = enc['color'];
      }
      if (opacityEnc) {
        trailEnc['opacity'] = { value: 0.3 };
        pointEnc['opacity'] = opacityEnc;
      }
      base['layer'] = [
        { mark: spec['mark'], encoding: trailEnc },
        { mark: { type: 'point', size: 80, filled: true, cursor: 'pointer' }, encoding: pointEnc },
      ];
    } else {
      base['mark'] = spec['mark'];
      const enc = { ...(spec['encoding'] || {}) };
      if (opacityEnc) {
        enc['opacity'] = opacityEnc;
      }
      base['encoding'] = enc;
    }

    return base;
  }

  private renderSelectableChart(
    el: HTMLDivElement,
    spec: Record<string, any>,
    data: Record<string, any>[],
    selectedRows: Set<number>,
  ): void {
    const stamped = this.stampData(data, selectedRows);
    const containerWidth = el.clientWidth - 24;
    const fullSpec = this.buildSpec(spec, stamped, selectedRows, containerWidth) as VisualizationSpec;
    console.log('[vega-spec:shoebox]', fullSpec);
    embed(el, fullSpec, { actions: false, renderer: 'svg' }).then(({ view }) => {
      view.addEventListener('click', (_event, item) => {
        if (item?.datum?._vi == null || !this.viewingDetail) return;
        const idx = item.datum._vi as number;
        if (this.selectedRows.has(idx)) {
          this.selectedRows.delete(idx);
        } else {
          this.selectedRows.add(idx);
        }
        this.selectedRows = new Set(this.selectedRows);
        this.rerenderChart();
        this.cdr.detectChanges();
      });
    }).catch(() => {});
  }

  private renderLockedChart(
    el: HTMLDivElement,
    spec: Record<string, any>,
    data: Record<string, any>[],
    selectedRows: Set<number>,
  ): void {
    const stamped = this.stampData(data, selectedRows);
    const containerWidth = el.clientWidth - 24;
    const fullSpec = this.buildSpec(spec, stamped, selectedRows, containerWidth) as VisualizationSpec;
    console.log('[vega-spec:evidence]', fullSpec);
    embed(el, fullSpec, { actions: false, renderer: 'svg' }).catch(() => {});
  }

  private rerenderChart(): void {
    if (!this.chartContainerEl || !this.viewingDetail?.chart_spec) return;
    this.renderSelectableChart(
      this.chartContainerEl.nativeElement,
      this.viewingDetail.chart_spec,
      this.viewingDetail.result,
      this.selectedRows,
    );
  }

  clearSelection(): void {
    this.selectedRows = new Set();
    this.rerenderChart();
  }

  closeDetail(): void {
    this.viewingDetail = null;
    this.selectedRows = new Set();
    this.addingEvidence = false;
    this.evidenceText = '';
  }

  triggerAiSearch(): void {
    this.schemaSvc.triggerAiSearch(this.workspaceId).subscribe();
  }

  triggerAiExtract(): void {
    if (this.shoeboxItems.length === 0) return;
    this.schemaSvc.triggerAiExtract(this.workspaceId).subscribe();
  }

  triggerAiBuildCase(): void {
    if (this.evidenceItems.length === 0) return;
    if (this.knownSuggestionIds.size >= 5) return;
    this.schemaSvc.triggerAiBuildCase(this.workspaceId).subscribe();
  }

  loadShoebox(): void {
    this.shoeboxSvc.list(this.workspaceId).subscribe((items) => {
      if (this.shoeboxInitialLoad) {
        this.shoeboxItems = items;
        this.knownShoeboxIds = new Set(items.map((i) => i.id));
        this.shoeboxInitialLoad = false;
        this.resortShoebox();
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
      this.resortShoebox();
      if (freshAiIds.length > 0) {
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
      this.sortedShoebox = this.sortedShoebox.filter((i) => i.id !== item.id);
    });
  }

  toggleRow(index: number): void {
    if (this.selectedRows.has(index)) {
      this.selectedRows.delete(index);
    } else {
      this.selectedRows.add(index);
    }
    this.selectedRows = new Set(this.selectedRows);
    this.rerenderChart();
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
    this.rerenderChart();
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

  private updateFilteredEvidence(): void {
    this.knownSuggestionIds = this.collectSuggestionIds(this.schemaData);
    const evidenceMap = new Map(this.evidenceItems.map((e) => [e.id, e]));
    this.schemaResolvedItems = this.resolveNodes(this.schemaData, evidenceMap);
    this.recomputeScores(evidenceMap);
  }

  private recomputeScores(evidenceMap: Map<string, EvidenceItemSummary>): void {
    const schemaTexts = this.collectSchemaTexts(this.schemaData, evidenceMap);
    const schemaIds = new Set(allEvidenceIds(this.schemaData));

    this.shoeboxScores.clear();
    if (schemaTexts.length > 0) {
      for (const item of this.shoeboxItems) {
        this.shoeboxScores.set(item.id, maxOverlap(item.explanation, schemaTexts));
      }
      this.sortedShoebox = [...this.shoeboxItems].sort(
        (a, b) => (this.shoeboxScores.get(b.id) ?? 0) - (this.shoeboxScores.get(a.id) ?? 0)
      );
    } else {
      this.sortedShoebox = [...this.shoeboxItems];
    }

    const filtered = this.evidenceItems.filter((item) => !schemaIds.has(item.id));
    this.evidenceScores.clear();
    if (schemaTexts.length > 0) {
      for (const item of filtered) {
        this.evidenceScores.set(item.id, maxOverlap(item.content, schemaTexts));
      }
      this.sortedEvidence = filtered.sort(
        (a, b) => (this.evidenceScores.get(b.id) ?? 0) - (this.evidenceScores.get(a.id) ?? 0)
      );
    } else {
      this.sortedEvidence = filtered;
    }
  }

  private collectSchemaTexts(
    nodes: SchemaNode[],
    evidenceMap: Map<string, EvidenceItemSummary>,
  ): string[] {
    const texts: string[] = [];
    const walk = (ns: SchemaNode[]) => {
      for (const node of ns) {
        if (node.type === 'evidence' && node.suggestion) continue;
        if (node.type === 'frame') {
          const combined = [node.title, node.description].filter(Boolean).join(' ');
          if (combined) texts.push(combined);
        } else if (node.type === 'evidence') {
          const ev = evidenceMap.get(node.id);
          if (ev?.content) texts.push(ev.content);
        }
        if (node.children) walk(node.children);
      }
    };
    walk(nodes);
    return texts;
  }

  private resortShoebox(): void {
    const evidenceMap = new Map(this.evidenceItems.map((e) => [e.id, e]));
    this.recomputeScores(evidenceMap);
  }

  private resolveNodes(
    nodes: SchemaNode[],
    evidenceMap: Map<string, EvidenceItemSummary>,
  ): ResolvedNode[] {
    return nodes.map((node) => {
      const children = this.resolveNodes(node.children ?? [], evidenceMap);
      if (node.type === 'evidence') {
        return {
          type: 'evidence' as const,
          id: node.id,
          rel: node.rel,
          suggestion: node.suggestion,
          evidence: evidenceMap.get(node.id),
          children,
        };
      }
      return {
        type: 'frame' as const,
        id: node.id,
        rel: node.rel,
        title: node.title,
        description: node.description,
        children,
      };
    });
  }

  isCancelled(node: ResolvedNode): boolean {
    return node.children.some(c => c.rel === 'cancel' && !c.suggestion && !this.isCancelled(c));
  }

  relIcon(rel: RelType): string {
    switch (rel) {
      case 'elaborate': return '+';
      case 'question': return '?';
      case 'cancel': return '✕';
    }
  }

  relLabel(rel: RelType): string {
    switch (rel) {
      case 'elaborate': return 'Elabora';
      case 'question': return 'Questiona';
      case 'cancel': return 'Cancela';
    }
  }

  cycleRel(event: Event, node: ResolvedNode): void {
    event.stopPropagation();
    if (node.suggestion) return;
    const cycle: RelType[] = ['elaborate', 'question', 'cancel'];
    const idx = cycle.indexOf(node.rel ?? 'elaborate');
    const nextRel = cycle[(idx + 1) % cycle.length];
    const location = this.findParentAndIndex(node.id, this.schemaResolvedItems);
    if (!location) return;
    this.schemaSvc.moveNode(
      this.workspaceId, node.id, location.parentId, location.index, nextRel
    ).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
    });
  }

  private findParentAndIndex(
    nodeId: string,
    nodes: ResolvedNode[],
    parentId?: string,
  ): { parentId: string | undefined; index: number } | null {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i].id === nodeId) {
        return { parentId, index: i };
      }
      const found = this.findParentAndIndex(nodeId, nodes[i].children, nodes[i].id);
      if (found) return found;
    }
    return null;
  }

  onDragStart(event: DragEvent, item: EvidenceItemSummary): void {
    event.dataTransfer?.setData('application/evidence', item.id);
  }

  private draggingNodeId: string | null = null;

  onSchemaDragStart(event: DragEvent, node: ResolvedNode): void {
    if (node.suggestion) {
      event.preventDefault();
      return;
    }
    event.stopPropagation();
    this.draggingNodeId = node.id;
    event.dataTransfer?.setData('application/schema-node', node.id);
    event.dataTransfer!.effectAllowed = 'move';
  }

  onSchemaDragover(event: DragEvent): void {
    event.preventDefault();
    if (this.dragoverRaf) return;
    this.dragoverRaf = true;
    requestAnimationFrame(() => {
      this.dragoverRaf = false;
      this.computeDropIndicator(event);
    });
  }

  private computeDropIndicator(event: DragEvent): void {
    const y = event.clientY;
    const target = event.target as HTMLElement;
    const nodeEl = target.closest('.schema-node[data-node-id]') as HTMLElement | null;

    if (nodeEl) {
      const rect = nodeEl.getBoundingClientRect();
      const relY = (y - rect.top) / rect.height;
      const nodeId = nodeEl.getAttribute('data-node-id')!;

      if (this.draggingNodeId && this.isDescendantOrSelf(nodeId, this.draggingNodeId)) {
        this.dropIndicator = null;
        return;
      }

      if (relY < 0.25) {
        const parentEl = nodeEl.parentElement?.closest(
          '.frame-children[data-node-id], .evidence-children[data-node-id], .schema-drop-zone[data-node-id]'
        ) as HTMLElement | null;
        if (parentEl) {
          const siblings = Array.from(parentEl.children).filter(c => c.classList.contains('schema-node'));
          const idx = siblings.indexOf(nodeEl);
          const pid = parentEl.getAttribute('data-node-id');
          this.dropIndicator = { parentId: pid === 'root' ? null : pid, index: Math.max(0, idx) };
          return;
        }
      }

      const innerContainer = nodeEl.querySelector(
        ':scope > .frame-children[data-node-id], :scope > .evidence-children[data-node-id]'
      ) as HTMLElement | null;
      if (innerContainer) {
        this.setIndicatorFromContainer(innerContainer, y);
      } else {
        this.dropIndicator = { parentId: nodeId, index: 0 };
      }
      return;
    }

    const childrenEl = target.closest(
      '.frame-children[data-node-id], .evidence-children[data-node-id]'
    ) as HTMLElement | null;
    if (childrenEl) {
      this.setIndicatorFromContainer(childrenEl, y);
      return;
    }

    const rootEl = target.closest('.schema-drop-zone[data-node-id]') as HTMLElement | null;
    if (rootEl && this.draggingNodeId) {
      this.setIndicatorFromContainer(rootEl, y);
    } else {
      this.dropIndicator = null;
    }
  }

  private setIndicatorFromContainer(containerEl: HTMLElement, y: number): void {
    const parentId = containerEl.getAttribute('data-node-id');
    const isRoot = parentId === 'root';
    const schemaChildren = Array.from(containerEl.children).filter(
      (el) => el.classList.contains('schema-node')
    );
    let index = schemaChildren.length;
    for (let i = 0; i < schemaChildren.length; i++) {
      const rect = schemaChildren[i].getBoundingClientRect();
      if (y < rect.top + rect.height / 2) {
        index = i;
        break;
      }
    }
    this.dropIndicator = { parentId: isRoot ? null : parentId, index };
  }

  private isDescendantOrSelf(nodeId: string, ancestorId: string): boolean {
    if (nodeId === ancestorId) return true;
    const walk = (nodes: ResolvedNode[]): boolean => {
      for (const n of nodes) {
        if (n.id === ancestorId) {
          return this.findInTree(n.children, nodeId);
        }
        if (walk(n.children)) return true;
      }
      return false;
    };
    return walk(this.schemaResolvedItems);
  }

  private findInTree(nodes: ResolvedNode[], id: string): boolean {
    for (const n of nodes) {
      if (n.id === id) return true;
      if (this.findInTree(n.children, id)) return true;
    }
    return false;
  }

  onSchemaDragleave(event: DragEvent): void {
    const target = event.currentTarget as HTMLElement;
    const related = event.relatedTarget as Node | null;
    if (related && target.contains(related)) return;
    this.dropIndicator = null;
    this.draggingNodeId = null;
  }

  onSchemaDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const indicator = this.dropIndicator;
    this.dropIndicator = null;
    this.draggingNodeId = null;

    const schemaNodeId = event.dataTransfer?.getData('application/schema-node');
    if (schemaNodeId) {
      const parentId = indicator?.parentId ?? undefined;
      const index = indicator?.index ?? undefined;
      this.schemaSvc.moveNode(this.workspaceId, schemaNodeId, parentId, index).subscribe((resp) => {
        this.schemaData = resp.data;
        this.updateFilteredEvidence();
      });
      return;
    }

    const evidenceId = event.dataTransfer?.getData('application/evidence');
    if (!evidenceId) return;
    const parentId = indicator?.parentId ?? undefined;
    if (parentId === undefined) return;
    const index = indicator?.index ?? undefined;

    const item = this.evidenceItems.find((e) => e.id === evidenceId);
    if (item && this.isUncertain(item)) {
      this.pendingDrop = { evidenceId, parentId, index };
      this.viewEvidenceItem(item);
      return;
    }

    this.schemaSvc.addEvidence(this.workspaceId, evidenceId, parentId, index).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
    });
  }

  removeSchemaNode(event: Event, node: ResolvedNode): void {
    event.stopPropagation();
    if (node.type === 'frame') {
      this.schemaSvc.removeFrame(this.workspaceId, node.id).subscribe((resp) => {
        this.schemaData = resp.data;
        this.updateFilteredEvidence();
      });
    } else {
      this.schemaSvc.removeEvidence(this.workspaceId, node.id).subscribe((resp) => {
        this.schemaData = resp.data;
        this.updateFilteredEvidence();
      });
    }
  }

  createNewFrame(): void {
    this.schemaSvc.createFrame(this.workspaceId, '').subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
      const newFrame = resp.data[resp.data.length - 1];
      if (newFrame?.type === 'frame') {
        this.startEditingFrame(newFrame.id);
      }
    });
  }

  startEditingFrame(frameId: string): void {
    this.editingFrameId = frameId;
    setTimeout(() => {
      const input = document.querySelector('.frame-title-input') as HTMLInputElement | null;
      input?.focus();
      input?.select();
    });
  }

  saveFrameTitle(event: Event, frameId: string): void {
    const input = event.target as HTMLInputElement;
    const title = input.value.trim();
    this.editingFrameId = null;
    this.schemaSvc.updateFrame(this.workspaceId, frameId, title).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
    });
  }

  startEditingDesc(frameId: string): void {
    this.editingDescId = frameId;
    setTimeout(() => {
      const textarea = document.querySelector('.frame-desc-input') as HTMLTextAreaElement | null;
      if (textarea) {
        textarea.focus();
        textarea.select();
      }
    });
  }

  saveFrameDesc(event: Event, frameId: string): void {
    const textarea = event.target as HTMLTextAreaElement;
    const description = textarea.value.trim();
    this.editingDescId = null;
    this.schemaSvc.updateFrame(this.workspaceId, frameId, undefined, description).subscribe((resp) => {
      this.schemaData = resp.data;
      this.updateFilteredEvidence();
    });
  }

  private collectSuggestionIds(nodes: SchemaNode[]): Set<string> {
    const ids = new Set<string>();
    for (const node of nodes) {
      if (node.type === 'evidence' && node.suggestion) {
        ids.add(node.id);
      }
      if (node.children) {
        for (const id of this.collectSuggestionIds(node.children)) {
          ids.add(id);
        }
      }
    }
    return ids;
  }

  private pollAll(): void {
    this.schemaSvc.poll(this.workspaceId).subscribe((resp) => {
      this.aiSearchRunning = resp.ai_search_running;
      this.aiExtractRunning = resp.ai_extract_running;
      this.aiBuildCaseRunning = resp.ai_build_case_running;

      // shoebox
      if (this.shoeboxInitialLoad) {
        this.shoeboxItems = resp.shoebox;
        this.knownShoeboxIds = new Set(resp.shoebox.map((i) => i.id));
        this.shoeboxInitialLoad = false;
      } else {
        const freshShoeboxAiIds: string[] = [];
        for (const item of resp.shoebox) {
          if (!this.knownShoeboxIds.has(item.id) && item.ai_authored) {
            freshShoeboxAiIds.push(item.id);
          }
        }
        this.shoeboxItems = resp.shoebox;
        this.knownShoeboxIds = new Set(resp.shoebox.map((i) => i.id));
        if (freshShoeboxAiIds.length > 0) {
          for (const id of freshShoeboxAiIds) {
            this.newShoeboxIds.add(id);
            this.unseenShoeboxIds.add(id);
          }
          this.newShoeboxIds = new Set(this.newShoeboxIds);
          this.unseenShoeboxIds = new Set(this.unseenShoeboxIds);
          setTimeout(() => {
            for (const id of freshShoeboxAiIds) {
              this.newShoeboxIds.delete(id);
            }
            this.newShoeboxIds = new Set(this.newShoeboxIds);
          }, 2500);
        }
      }

      // evidence
      if (this.evidenceInitialLoad) {
        this.evidenceItems = resp.evidence;
        this.knownEvidenceIds = new Set(resp.evidence.map((i) => i.id));
        this.evidenceInitialLoad = false;
      } else {
        const freshEvidenceAiIds: string[] = [];
        for (const item of resp.evidence) {
          if (!this.knownEvidenceIds.has(item.id) && item.ai_authored) {
            freshEvidenceAiIds.push(item.id);
          }
        }
        this.evidenceItems = resp.evidence;
        this.knownEvidenceIds = new Set(resp.evidence.map((i) => i.id));
        if (freshEvidenceAiIds.length > 0) {
          for (const id of freshEvidenceAiIds) {
            this.newEvidenceIds.add(id);
            this.unseenEvidenceIds.add(id);
          }
          this.newEvidenceIds = new Set(this.newEvidenceIds);
          this.unseenEvidenceIds = new Set(this.unseenEvidenceIds);
          setTimeout(() => {
            for (const id of freshEvidenceAiIds) {
              this.newEvidenceIds.delete(id);
            }
            this.newEvidenceIds = new Set(this.newEvidenceIds);
          }, 2500);
        }
      }

      // schematization
      if (!this.editingFrameId && !this.editingDescId) {
        this.knownSuggestionIds = this.collectSuggestionIds(resp.schematization.data);
        this.schemaData = resp.schematization.data;
      }

      this.updateFilteredEvidence();
    });
  }

  isUncertain(item: { ai_authored: boolean; approved: boolean }): boolean {
    return item.ai_authored && !item.approved;
  }

  onEvidenceNodeClick(event: Event, item: EvidenceItemSummary, node?: ResolvedNode): void {
    event.stopPropagation();
    this.viewingSuggestionNodeId = node?.suggestion ? node.id : null;
    this.viewEvidenceItem(item);
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
        this.evidenceSourceShoebox = shoebox;
        this.evidenceSelectedRows = new Set(full.rows);
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
    this.pendingDrop = null;
    this.viewingSuggestionNodeId = null;
    this.viewingEvidence = null;
    this.evidenceSourceShoebox = null;
    this.evidenceSourceExplanation = '';
    this.evidenceSourceData = [];
    this.correctingEvidence = false;
    this.confirmingReject = false;
    this.correctText = '';
    this.clearVerifyTimer();
  }

  approveEvidence(): void {
    if (!this.viewingEvidence) return;
    const drop = this.pendingDrop;
    const suggestionNodeId = this.viewingSuggestionNodeId;
    this.pendingDrop = null;
    this.viewingSuggestionNodeId = null;
    this.evidenceSvc.approve(this.workspaceId, this.viewingEvidence.id).subscribe(() => {
      if (suggestionNodeId) {
        this.schemaSvc.approveSuggestion(this.workspaceId, suggestionNodeId).subscribe((resp) => {
          this.schemaData = resp.data;
          this.updateFilteredEvidence();
        });
      } else if (drop) {
        this.schemaSvc.addEvidence(this.workspaceId, drop.evidenceId, drop.parentId, drop.index).subscribe((resp) => {
          this.schemaData = resp.data;
          this.updateFilteredEvidence();
        });
      }
      this.closeEvidenceDetail();
      this.loadEvidence();
    });
  }

  rejectEvidence(): void {
    if (!this.viewingEvidence) return;
    const suggestionNodeId = this.viewingSuggestionNodeId;
    this.pendingDrop = null;
    this.viewingSuggestionNodeId = null;
    this.evidenceSvc.reject(this.workspaceId, this.viewingEvidence.id).subscribe(() => {
      if (suggestionNodeId) {
        this.schemaSvc.removeEvidence(this.workspaceId, suggestionNodeId).subscribe((resp) => {
          this.schemaData = resp.data;
          this.updateFilteredEvidence();
        });
      }
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
    const drop = this.pendingDrop;
    const suggestionNodeId = this.viewingSuggestionNodeId;
    this.pendingDrop = null;
    this.viewingSuggestionNodeId = null;
    this.evidenceSvc
      .correct(this.workspaceId, this.viewingEvidence.id, this.correctText.trim())
      .subscribe(() => {
        if (suggestionNodeId) {
          this.schemaSvc.approveSuggestion(this.workspaceId, suggestionNodeId).subscribe((resp) => {
            this.schemaData = resp.data;
            this.updateFilteredEvidence();
            });
        } else if (drop) {
          this.schemaSvc.addEvidence(this.workspaceId, drop.evidenceId, drop.parentId, drop.index).subscribe((resp) => {
            this.schemaData = resp.data;
            this.updateFilteredEvidence();
            });
        }
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
      this.sortedEvidence = this.sortedEvidence.filter((i) => i.id !== item.id);
    });
  }
}
