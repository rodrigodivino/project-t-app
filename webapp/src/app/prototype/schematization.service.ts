import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ShoeboxItemSummary } from './shoebox.service';
import { EvidenceItemSummary } from './evidence.service';

export type RelType = 'elaborate' | 'question' | 'cancel';

export interface SchemaEvidenceNode {
  type: 'evidence';
  id: string;
  rel?: RelType;
  suggestion?: boolean;
  description?: string;
  children?: SchemaNode[];
}

export interface SchemaFrameNode {
  type: 'frame';
  id: string;
  title: string;
  description: string;
  rel?: RelType;
  children?: SchemaNode[];
}

export type SchemaNode = SchemaEvidenceNode | SchemaFrameNode;

export type SchematizationData = SchemaNode[];

export interface SchematizationResponse {
  workspace_id: string;
  data: SchematizationData;
}

export function allEvidenceIds(tree: SchemaNode[]): string[] {
  const ids: string[] = [];
  for (const node of tree) {
    if (node.type === 'evidence' && !node.suggestion) {
      ids.push(node.id);
    }
    if (node.children) {
      ids.push(...allEvidenceIds(node.children));
    }
  }
  return ids;
}

@Injectable({
  providedIn: 'root',
})
export class SchematizationService {
  constructor(private http: HttpClient) {}

  get(workspaceId: string): Observable<SchematizationResponse> {
    return this.http.get<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization`
    );
  }

  addEvidence(
    workspaceId: string,
    evidenceId: string,
    parentId?: string,
    index?: number,
    rel: RelType = 'elaborate',
    suggestion = false,
  ): Observable<SchematizationResponse> {
    const body: Record<string, unknown> = { evidence_id: evidenceId, rel };
    if (parentId !== undefined) body['parent_id'] = parentId;
    if (index !== undefined) body['index'] = index;
    if (suggestion) body['suggestion'] = true;
    return this.http.post<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/evidence`,
      body
    );
  }

  removeEvidence(
    workspaceId: string,
    evidenceId: string
  ): Observable<SchematizationResponse> {
    return this.http.delete<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/evidence/${evidenceId}`
    );
  }

  createFrame(
    workspaceId: string,
    title: string,
    description: string = '',
  ): Observable<SchematizationResponse> {
    return this.http.post<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/frames`,
      { title, description }
    );
  }

  updateFrame(
    workspaceId: string,
    frameId: string,
    title?: string,
    description?: string,
  ): Observable<SchematizationResponse> {
    const body: Record<string, unknown> = {};
    if (title !== undefined) body['title'] = title;
    if (description !== undefined) body['description'] = description;
    return this.http.patch<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/frames/${frameId}`,
      body
    );
  }

  removeFrame(
    workspaceId: string,
    frameId: string,
  ): Observable<SchematizationResponse> {
    return this.http.delete<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/frames/${frameId}`
    );
  }

  moveNode(
    workspaceId: string,
    nodeId: string,
    parentId?: string,
    index?: number,
    rel: RelType = 'elaborate',
  ): Observable<SchematizationResponse> {
    const body: Record<string, unknown> = { rel };
    if (parentId !== undefined) body['parent_id'] = parentId;
    if (index !== undefined) body['index'] = index;
    return this.http.post<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/nodes/${nodeId}/move`,
      body
    );
  }

  updateNode(
    workspaceId: string,
    nodeId: string,
    description?: string,
  ): Observable<SchematizationResponse> {
    const body: Record<string, unknown> = {};
    if (description !== undefined) body['description'] = description;
    return this.http.patch<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/nodes/${nodeId}`,
      body
    );
  }

  approveSuggestion(
    workspaceId: string,
    nodeId: string,
  ): Observable<SchematizationResponse> {
    return this.http.patch<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/nodes/${nodeId}/approve-suggestion`,
      {}
    );
  }

  triggerAiSearch(workspaceId: string): Observable<void> {
    return this.http.post<void>(
      `/api/workspaces/${workspaceId}/schematization/ai-search`,
      {}
    );
  }

  triggerAiExtract(workspaceId: string): Observable<void> {
    return this.http.post<void>(
      `/api/workspaces/${workspaceId}/schematization/ai-extract`,
      {}
    );
  }

  triggerAiBuildCase(workspaceId: string): Observable<void> {
    return this.http.post<void>(
      `/api/workspaces/${workspaceId}/schematization/ai-build-case`,
      {}
    );
  }

  triggerAiStory(workspaceId: string): Observable<void> {
    return this.http.post<void>(
      `/api/workspaces/${workspaceId}/schematization/ai-story`,
      {}
    );
  }

  poll(workspaceId: string): Observable<WorkspacePollResponse> {
    return this.http.get<WorkspacePollResponse>(
      `/api/workspaces/${workspaceId}/poll`
    );
  }
}

export interface WorkspacePollResponse {
  shoebox: ShoeboxItemSummary[];
  evidence: EvidenceItemSummary[];
  schematization: SchematizationResponse;
  story: string;
  ai_search_running: boolean;
  ai_extract_running: boolean;
  ai_build_case_running: boolean;
  ai_story_running: boolean;
}
