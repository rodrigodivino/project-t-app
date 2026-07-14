import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SourceDocument {
  id: string;
  filename: string;
  content_type: string;
}

@Injectable({
  providedIn: 'root',
})
export class SourcesService {
  constructor(private http: HttpClient) {}

  list(workspaceId: string): Observable<SourceDocument[]> {
    return this.http.get<SourceDocument[]>(
      `/api/workspaces/${workspaceId}/sources`
    );
  }

  upload(workspaceId: string, file: File): Observable<SourceDocument> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<SourceDocument>(
      `/api/workspaces/${workspaceId}/sources`,
      form
    );
  }

  delete(workspaceId: string, id: string): Observable<void> {
    return this.http.delete<void>(
      `/api/workspaces/${workspaceId}/sources/${id}`
    );
  }
}
