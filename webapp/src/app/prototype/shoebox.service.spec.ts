import { ShoeboxService, ShoeboxItem } from './shoebox.service';
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
    const items: ShoeboxItem[] = [
      { id: '1', source_document_id: 'doc-1' },
    ];
    http.get.mockReturnValue(of(items));
    const svc = new ShoeboxService(http as any);
    svc.list(WS).subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/shoebox`);
      expect(result).toEqual(items);
      done();
    });
  });

  it('add sends POST with source_document_id', (done) => {
    const http = mockHttp();
    const item: ShoeboxItem = { id: '2', source_document_id: 'doc-2' };
    http.post.mockReturnValue(of(item));
    const svc = new ShoeboxService(http as any);
    svc.add(WS, 'doc-2').subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/shoebox`,
        { source_document_id: 'doc-2' }
      );
      expect(result).toEqual(item);
      done();
    });
  });

  it('remove calls DELETE /api/workspaces/:id/shoebox/:docId', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of(undefined));
    const svc = new ShoeboxService(http as any);
    svc.remove(WS, 'doc-1').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/shoebox/doc-1`
      );
      done();
    });
  });
});
