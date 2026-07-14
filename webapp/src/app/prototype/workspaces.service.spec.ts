import { WorkspacesService, Workspace } from './workspaces.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  };
}

describe('WorkspacesService', () => {
  it('list calls GET /api/workspaces', (done) => {
    const http = mockHttp();
    const items: Workspace[] = [{ id: '1', name: 'WS1' }];
    http.get.mockReturnValue(of(items));
    const svc = new WorkspacesService(http as any);
    svc.list().subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith('/api/workspaces');
      expect(result).toEqual(items);
      done();
    });
  });

  it('create calls POST /api/workspaces', (done) => {
    const http = mockHttp();
    const ws: Workspace = { id: '2', name: 'New' };
    http.post.mockReturnValue(of(ws));
    const svc = new WorkspacesService(http as any);
    svc.create('New').subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith('/api/workspaces', { name: 'New' });
      expect(result).toEqual(ws);
      done();
    });
  });

  it('delete calls DELETE /api/workspaces/:id', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of(undefined));
    const svc = new WorkspacesService(http as any);
    svc.delete('abc').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith('/api/workspaces/abc');
      done();
    });
  });
});
