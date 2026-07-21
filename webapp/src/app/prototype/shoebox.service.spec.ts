import { ShoeboxService, ShoeboxItemSummary, ShoeboxItemFull } from './shoebox.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  };
}

const WS = 'ws-123';

describe('ShoeboxService', () => {
  it('list calls GET /api/workspaces/:id/shoebox', (done) => {
    const http = mockHttp();
    const items: ShoeboxItemSummary[] = [
      { id: '1', query: 'SELECT * FROM post_rede_social_himark', explanation: 'test', ai_authored: false, added_at: '2026-07-21T00:00:00Z' },
    ];
    http.get.mockReturnValue(of(items));
    const svc = new ShoeboxService(http as any);
    svc.list(WS).subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/shoebox`);
      expect(result).toEqual(items);
      done();
    });
  });

  it('add sends POST with query, explanation, result', (done) => {
    const http = mockHttp();
    const item: ShoeboxItemFull = {
      id: '2',
      query: 'SELECT * FROM post_rede_social_himark LIMIT 1',
      explanation: 'Adicionado manualmente pelo usuário',
      result: [{ time: '2020-04-06', location: 'Broadview' }],
      ai_authored: false,
      added_at: '2026-07-21T00:00:00Z',
    };
    http.post.mockReturnValue(of(item));
    const svc = new ShoeboxService(http as any);
    svc.add(WS, item.query, item.explanation, item.result).subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/shoebox`,
        { query: item.query, explanation: item.explanation, result: item.result }
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('get calls GET /api/workspaces/:id/shoebox/:itemId', (done) => {
    const http = mockHttp();
    const item: ShoeboxItemFull = {
      id: '3',
      query: 'SELECT * FROM post_rede_social_himark',
      explanation: 'test',
      result: [],
      ai_authored: true,
      added_at: '2026-07-21T00:00:00Z',
    };
    http.get.mockReturnValue(of(item));
    const svc = new ShoeboxService(http as any);
    svc.get(WS, '3').subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/shoebox/3`);
      expect(result).toEqual(item);
      done();
    });
  });

  it('remove calls DELETE /api/workspaces/:id/shoebox/:itemId', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of(undefined));
    const svc = new ShoeboxService(http as any);
    svc.remove(WS, 'item-1').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/shoebox/item-1`
      );
      done();
    });
  });
});
