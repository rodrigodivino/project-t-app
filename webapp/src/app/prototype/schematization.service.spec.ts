import { SchematizationService, SchematizationResponse } from './schematization.service';
import { of } from 'rxjs';

function mockHttp() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  };
}

const WS = 'ws-123';

describe('SchematizationService', () => {
  it('get calls GET /api/workspaces/:id/schematization', (done) => {
    const http = mockHttp();
    const resp: SchematizationResponse = {
      workspace_id: WS,
      data: { frames: [], evidence: [], relationships: [] },
    };
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
      data: { frames: [], evidence: ['ev-1'], relationships: [] },
    };
    http.post.mockReturnValue(of(resp));
    const svc = new SchematizationService(http as any);
    svc.addEvidence(WS, 'ev-1').subscribe((result) => {
      expect(http.post).toHaveBeenCalledWith(
        `/api/workspaces/${WS}/schematization/evidence`,
        { evidence_id: 'ev-1' }
      );
      expect(result).toEqual(resp);
      done();
    });
  });

  it('removeEvidence calls DELETE', (done) => {
    const http = mockHttp();
    const resp: SchematizationResponse = {
      workspace_id: WS,
      data: { frames: [], evidence: [], relationships: [] },
    };
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
});
