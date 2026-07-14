import { SourcesService, SourceDocument } from './sources.service';
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
  it('list calls GET /api/workspaces/:id/sources', (done) => {
    const http = mockHttp();
    const docs: SourceDocument[] = [
      { id: '1', filename: 'a.pdf', content_type: 'application/pdf' },
    ];
    http.get.mockReturnValue(of(docs));
    const svc = new SourcesService(http as any);
    svc.list(WS).subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/sources`);
      expect(result).toEqual(docs);
      done();
    });
  });

  it('upload sends FormData to POST /api/workspaces/:id/sources', (done) => {
    const http = mockHttp();
    const doc: SourceDocument = {
      id: '2',
      filename: 'b.pdf',
      content_type: 'application/pdf',
    };
    http.post.mockReturnValue(of(doc));
    const svc = new SourcesService(http as any);
    const file = new File(['content'], 'b.pdf', { type: 'application/pdf' });
    svc.upload(WS, file).subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/sources`,
        expect.any(FormData)
      );
      expect(result).toEqual(doc);
      done();
    });
  });

  it('delete calls DELETE /api/workspaces/:id/sources/:docId', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of(undefined));
    const svc = new SourcesService(http as any);
    svc.delete(WS, 'abc').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/sources/abc`
      );
      done();
    });
  });
});
