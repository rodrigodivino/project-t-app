import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class SourcesService {
  constructor(private http: HttpClient) {}

  query(workspaceId: string, sql: string): Observable<Record<string, any>[]> {
    return this.http.post<Record<string, any>[]>(
      `/api/workspaces/${workspaceId}/sources/query`,
      { query: sql }
    );
  }
}
