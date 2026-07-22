import {
  SchematizationService,
  SchematizationResponse,
  allEvidenceIds,
  SchemaNode,
} from './schematization.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
  };
}

const WS = 'ws-123';

describe('allEvidenceIds', () => {
  it('collects IDs from flat tree', () => {
    const tree: SchemaNode[] = [
      { type: 'evidence', id: 'e1' },
      { type: 'frame', id: 'f1', title: '', description: '', children: [] },
      { type: 'evidence', id: 'e2' },
    ];
    expect(allEvidenceIds(tree)).toEqual(['e1', 'e2']);
  });

  it('collects IDs from nested tree', () => {
    const tree: SchemaNode[] = [
      {
        type: 'frame', id: 'f1', title: '', description: '',
        children: [
          { type: 'evidence', id: 'e1', rel: 'elaborate' },
          {
            type: 'frame', id: 'f2', title: '', description: '', rel: 'elaborate',
            children: [{ type: 'evidence', id: 'e2', rel: 'question' }],
          },
        ],
      },
      { type: 'evidence', id: 'e3' },
    ];
    expect(allEvidenceIds(tree)).toEqual(['e1', 'e2', 'e3']);
  });
});

describe('SchematizationService', () => {
  it('get calls GET /api/workspaces/:id/schematization', (done) => {
    const http = mockHttp();
    const resp: SchematizationResponse = { workspace_id: WS, data: [] };
    http.get.mockReturnValue(of(resp));
    const svc = new SchematizationService(http as any);
    svc.get(WS).subscribe((result) => {
      expect(http.get).toHaveBeenCalledWith(`/api/workspaces/${WS}/schematization`);
      expect(result).toEqual(resp);
      done();
    });
  });

  it('addEvidence calls POST with evidence_id', (done) => {
    const http = mockHttp();
    const resp: SchematizationResponse = {
      workspace_id: WS,
      data: [{ type: 'evidence', id: 'ev-1' }],
    };
    http.post.mockReturnValue(of(resp));
    const svc = new SchematizationService(http as any);
    svc.addEvidence(WS, 'ev-1').subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/evidence`,
        { evidence_id: 'ev-1', rel: 'elaborate' }
      );
      expect(result).toEqual(resp);
      done();
    });
  });

  it('addEvidence passes parent_id and index when given', (done) => {
    const http = mockHttp();
    http.post.mockReturnValue(of({ workspace_id: WS, data: [] }));
    const svc = new SchematizationService(http as any);
    svc.addEvidence(WS, 'ev-1', 'f-1', 0, 'question').subscribe(() => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/evidence`,
        { evidence_id: 'ev-1', parent_id: 'f-1', index: 0, rel: 'question' }
      );
      done();
    });
  });

  it('removeEvidence calls DELETE', (done) => {
    const http = mockHttp();
    const resp: SchematizationResponse = { workspace_id: WS, data: [] };
    http.delete.mockReturnValue(of(resp));
    const svc = new SchematizationService(http as any);
    svc.removeEvidence(WS, 'ev-1').subscribe((result) => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/evidence/ev-1`
      );
      expect(result).toEqual(resp);
      done();
    });
  });

  it('createFrame calls POST /frames', (done) => {
    const http = mockHttp();
    http.post.mockReturnValue(of({ workspace_id: WS, data: [] }));
    const svc = new SchematizationService(http as any);
    svc.createFrame(WS, 'H1', 'desc').subscribe(() => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/frames`,
        { title: 'H1', description: 'desc' }
      );
      done();
    });
  });

  it('updateFrame calls PATCH /frames/:id', (done) => {
    const http = mockHttp();
    http.patch.mockReturnValue(of({ workspace_id: WS, data: [] }));
    const svc = new SchematizationService(http as any);
    svc.updateFrame(WS, 'f-1', 'New Title').subscribe(() => {
      expect(http.patch).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/frames/f-1`,
        { title: 'New Title' }
      );
      done();
    });
  });

  it('removeFrame calls DELETE /frames/:id', (done) => {
    const http = mockHttp();
    http.delete.mockReturnValue(of({ workspace_id: WS, data: [] }));
    const svc = new SchematizationService(http as any);
    svc.removeFrame(WS, 'f-1').subscribe(() => {
      expect(http.delete).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/frames/f-1`
      );
      done();
    });
  });

  it('moveNode calls POST /nodes/:id/move', (done) => {
    const http = mockHttp();
    http.post.mockReturnValue(of({ workspace_id: WS, data: [] }));
    const svc = new SchematizationService(http as any);
    svc.moveNode(WS, 'n-1', 'p-1', 2, 'cancel').subscribe(() => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/nodes/n-1/move`,
        { parent_id: 'p-1', index: 2, rel: 'cancel' }
      );
      done();
    });
  });
});
