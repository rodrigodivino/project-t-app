import { EvidenceService, EvidenceItemSummary, EvidenceItemFull } from './evidence.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  };
}

const WS = 'ws-123';

describe('EvidenceService', () => {
  it('list calls GET /api/workspaces/:id/evidence', (done) => {
    const http = mockHttp();
    const items: EvidenceItemSummary[] = [
      { id: '1', shoebox_id: 'sb-1', content: 'rising damage', ai_authored: false, approved: false, rejected: false, created_at: '2026-07-21T00:00:00Z' },
    ];
    http.get.mockReturnValue(of(items));
    const svc = new EvidenceService(http as any);
    svc.list(WS).subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/evidence`);
      expect(result).toEqual(items);
      done();
    });
  });

  it('add sends POST with shoebox_id, content, rows', (done) => {
    const http = mockHttp();
    const item: EvidenceItemFull = {
      id: '2',
      shoebox_id: 'sb-1',
      content: 'rising damage',
      rows: [0, 2],
      ai_authored: false,
      approved: false,
      rejected: false,
      created_at: '2026-07-21T00:00:00Z',
    };
    http.post.mockReturnValue(of(item));
    const svc = new EvidenceService(http as any);
    svc.add(WS, 'sb-1', 'rising damage', [0, 2]).subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/evidence`,
        { shoebox_id: 'sb-1', content: 'rising damage', rows: [0, 2] }
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('correct calls PATCH /correct with content', (done) => {
    const http = mockHttp();
    const item: EvidenceItemFull = {
      id: '2',
      shoebox_id: 'sb-1',
      content: 'corrected',
      rows: [0],
      ai_authored: false,
      approved: false,
      rejected: false,
      created_at: '2026-07-21T00:00:00Z',
    };
    http.patch.mockReturnValue(of(item));
    const svc = new EvidenceService(http as any);
    svc.correct(WS, '2', 'corrected').subscribe((result) => {
      expect(http.patch).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/evidence/2/correct`,
        { content: 'corrected' }
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('approve calls PATCH /approve', (done) => {
    const http = mockHttp();
    const item: EvidenceItemFull = {
      id: '4',
      shoebox_id: 'sb-1',
      content: 'text',
      rows: [0],
      ai_authored: true,
      approved: true,
      rejected: false,
      created_at: '2026-07-21T00:00:00Z',
    };
    http.patch.mockReturnValue(of(item));
    const svc = new EvidenceService(http as any);
    svc.approve(WS, '4').subscribe((result) => {
      expect(http.patch).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/evidence/4/approve`,
        {}
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('reject calls PATCH /reject', (done) => {
    const http = mockHttp();
    const item: EvidenceItemFull = {
      id: '5',
      shoebox_id: 'sb-1',
      content: 'text',
      rows: [0],
      ai_authored: true,
      approved: false,
      rejected: true,
      created_at: '2026-07-21T00:00:00Z',
    };
    http.patch.mockReturnValue(of(item));
    const svc = new EvidenceService(http as any);
    svc.reject(WS, '5').subscribe((result) => {
      expect(http.patch).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/evidence/5/reject`,
        {}
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('remove calls DELETE /api/workspaces/:id/evidence/:itemId', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of(undefined));
    const svc = new EvidenceService(http as any);
    svc.remove(WS, 'ev-1').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/evidence/ev-1`
      );
      done();
    });
  });
});
