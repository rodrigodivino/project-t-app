import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type RelType = 'elaborate' | 'question' | 'cancel';

export interface SchemaEvidenceNode {
  type: 'evidence';
  id: string;
  rel?: RelType;
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
    if (node.type === 'evidence') {
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
  ): Observable<SchematizationResponse> {
    const body: Record<string, unknown> = { evidence_id: evidenceId, rel };
    if (parentId !== undefined) body['parent_id'] = parentId;
    if (index !== undefined) body['index'] = index;
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
}
