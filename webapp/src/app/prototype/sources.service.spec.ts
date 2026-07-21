import { SourcesService } from './sources.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  };
}

const WS = 'ws-123';

describe('SourcesService', () => {
  it('query sends POST to /api/workspaces/:id/sources/query', (done) => {
    const http = mockHttp();
    const rows = [{ time: '2020-04-06', location: 'Broadview', account: 'user1', message: 'hello' }];
    http.post.mockReturnValue(of(rows));
    const svc = new SourcesService(http as any);
    svc.query(WS, 'SELECT * FROM post_rede_social_himark LIMIT 1').subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/sources/query`,
        { query: 'SELECT * FROM post_rede_social_himark LIMIT 1' }
      );
      expect(result).toEqual(rows);
      done();
    });
  });
});
