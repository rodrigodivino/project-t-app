import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface WebConfig {
  production: boolean;
}

@Injectable({ providedIn: 'root' })
export class WebConfigService {
  private config: WebConfig = { production: false };

  constructor(private http: HttpClient) {}

  load(): Promise<void> {
    return firstValueFrom(
      this.http.get<WebConfig>('/api/web-config')
    ).then((c) => {
      this.config = c;
    });
  }

  get production(): boolean {
    return this.config.production;
  }
}
