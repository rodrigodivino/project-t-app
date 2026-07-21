import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SchematizationData {
  frames: { id: string; title: string; description: string }[];
  evidence: string[];
  relationships: { source: string; target: string; type: string }[];
}

export interface SchematizationResponse {
  workspace_id: string;
  data: SchematizationData;
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
    evidenceId: string
  ): Observable<SchematizationResponse> {
    return this.http.post<SchematizationResponse>(
      `/api/workspaces/${workspaceId}/schematization/evidence`,
      { evidence_id: evidenceId }
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
}
