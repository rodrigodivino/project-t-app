import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface EvidenceItemSummary {
  id: string;
  shoebox_id: string;
  content: string;
  ai_authored: boolean;
  approved: boolean;
  rejected: boolean;
  created_at: string;
}

export interface EvidenceItemFull {
  id: string;
  shoebox_id: string;
  content: string;
  rows: number[];
  ai_authored: boolean;
  approved: boolean;
  rejected: boolean;
  created_at: string;
}

@Injectable({
  providedIn: 'root',
})
export class EvidenceService {
  constructor(private http: HttpClient) {}

  list(workspaceId: string): Observable<EvidenceItemSummary[]> {
    return this.http.get<EvidenceItemSummary[]>(
      `/api/workspaces/${workspaceId}/evidence`
    );
  }

  get(workspaceId: string, itemId: string): Observable<EvidenceItemFull> {
    return this.http.get<EvidenceItemFull>(
      `/api/workspaces/${workspaceId}/evidence/${itemId}`
    );
  }

  add(
    workspaceId: string,
    shoeboxId: string,
    content: string,
    rows: number[]
  ): Observable<EvidenceItemFull> {
    return this.http.post<EvidenceItemFull>(
      `/api/workspaces/${workspaceId}/evidence`,
      { shoebox_id: shoeboxId, content, rows }
    );
  }

  correct(
    workspaceId: string,
    itemId: string,
    content: string
  ): Observable<EvidenceItemFull> {
    return this.http.patch<EvidenceItemFull>(
      `/api/workspaces/${workspaceId}/evidence/${itemId}/correct`,
      { content }
    );
  }

  approve(workspaceId: string, itemId: string): Observable<EvidenceItemFull> {
    return this.http.patch<EvidenceItemFull>(
      `/api/workspaces/${workspaceId}/evidence/${itemId}/approve`,
      {}
    );
  }

  reject(workspaceId: string, itemId: string): Observable<EvidenceItemFull> {
    return this.http.patch<EvidenceItemFull>(
      `/api/workspaces/${workspaceId}/evidence/${itemId}/reject`,
      {}
    );
  }

  remove(workspaceId: string, itemId: string): Observable<void> {
    return this.http.delete<void>(
      `/api/workspaces/${workspaceId}/evidence/${itemId}`
    );
  }
}
