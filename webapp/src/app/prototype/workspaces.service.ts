import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Workspace {
  id: string;
  name: string;
}

@Injectable({
  providedIn: 'root',
})
export class WorkspacesService {
  constructor(private http: HttpClient) {}

  list(): Observable<Workspace[]> {
    return this.http.get<Workspace[]>('/api/workspaces');
  }

  create(name: string): Observable<Workspace> {
    return this.http.post<Workspace>('/api/workspaces', { name });
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`/api/workspaces/${id}`);
  }
}
