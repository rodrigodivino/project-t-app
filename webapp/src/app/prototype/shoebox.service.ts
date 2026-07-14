import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ShoeboxItem {
  id: string;
  source_document_id: string;
}

@Injectable({
  providedIn: 'root',
})
export class ShoeboxService {
  constructor(private http: HttpClient) {}

  list(workspaceId: string): Observable<ShoeboxItem[]> {
    return this.http.get<ShoeboxItem[]>(
      `/api/workspaces/${workspaceId}/shoebox`
    );
  }

  add(workspaceId: string, sourceDocumentId: string): Observable<ShoeboxItem> {
    return this.http.post<ShoeboxItem>(
      `/api/workspaces/${workspaceId}/shoebox`,
      { source_document_id: sourceDocumentId }
    );
  }

  remove(workspaceId: string, sourceDocumentId: string): Observable<void> {
    return this.http.delete<void>(
      `/api/workspaces/${workspaceId}/shoebox/${sourceDocumentId}`
    );
  }
}
