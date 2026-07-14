import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  healthStatus: 'pending' | 'ok' | 'error' = 'pending';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<{ status: string }>('/api/health').subscribe({
      next: () => (this.healthStatus = 'ok'),
      error: () => (this.healthStatus = 'error'),
    });
  }
}
