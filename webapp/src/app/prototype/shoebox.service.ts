import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ShoeboxItemSummary {
  id: string;
  query: string;
  explanation: string;
  ai_authored: boolean;
  added_at: string;
}

export interface ShoeboxItemFull {
  id: string;
  query: string;
  explanation: string;
  result: Record<string, any>[];
  chart_spec: Record<string, any> | null;
  ai_authored: boolean;
  added_at: string;
}

@Injectable({
  providedIn: 'root',
})
export class ShoeboxService {
  constructor(private http: HttpClient) {}

  list(workspaceId: string): Observable<ShoeboxItemSummary[]> {
    return this.http.get<ShoeboxItemSummary[]>(
      `/api/workspaces/${workspaceId}/shoebox`
    );
  }

  get(workspaceId: string, itemId: string): Observable<ShoeboxItemFull> {
    return this.http.get<ShoeboxItemFull>(
      `/api/workspaces/${workspaceId}/shoebox/${itemId}`
    );
  }

  add(
    workspaceId: string,
    query: string,
    explanation: string,
    result: Record<string, any>[],
    chartSpec: Record<string, any> | null = null,
  ): Observable<ShoeboxItemFull> {
    return this.http.post<ShoeboxItemFull>(
      `/api/workspaces/${workspaceId}/shoebox`,
      { query, explanation, result, chart_spec: chartSpec }
    );
  }

  generateChart(
    workspaceId: string,
    sql: string,
    explanation: string,
    rows: Record<string, any>[],
  ): Observable<{ chart_spec: Record<string, any> | null }> {
    return this.http.post<{ chart_spec: Record<string, any> | null }>(
      `/api/workspaces/${workspaceId}/shoebox/chart`,
      { sql, explanation, rows }
    );
  }

  remove(workspaceId: string, itemId: string): Observable<void> {
    return this.http.delete<void>(
      `/api/workspaces/${workspaceId}/shoebox/${itemId}`
    );
  }
}
