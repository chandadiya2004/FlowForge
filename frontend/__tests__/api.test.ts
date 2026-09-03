import { apiFetch, setTokens, getAccessToken } from '../src/lib/api';

describe('API Client 401 Token Refresh Logic', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('triggers /auth/refresh on 401, updates stored token, and retries request', async () => {
    setTokens('expired_token', 'valid_refresh_token');

    const mockFetch = jest.fn()
      // Call 1: Original request returns 401
      .mockResolvedValueOnce({
        status: 401,
        ok: false,
        json: async () => ({ detail: 'Token expired' }),
      })
      // Call 2: Refresh token request returns new access token
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({ access_token: 'fresh_new_token' }),
      })
      // Call 3: Retried original request with new token succeeds
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({ data: 'secret_workflow_data' }),
      });

    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await apiFetch<{ data: string }>('/workflows');

    expect(result).toEqual({ data: 'secret_workflow_data' });
    expect(mockFetch).toHaveBeenCalledTimes(3);

    // Call 2 was POST /auth/refresh
    expect(mockFetch.mock.calls[1][0]).toContain('/auth/refresh');

    // Call 3 was retried with new Bearer token
    const retriedHeaders = mockFetch.mock.calls[2][1]?.headers as Headers;
    expect(retriedHeaders.get('Authorization')).toBe('Bearer fresh_new_token');

    // localStorage updated
    expect(getAccessToken()).toBe('fresh_new_token');
  });

  it('clears tokens and throws session expired when refresh fails', async () => {
    setTokens('expired_token', 'bad_refresh_token');

    const mockFetch = jest.fn()
      // Call 1: 401 on API
      .mockResolvedValueOnce({
        status: 401,
        ok: false,
        json: async () => ({ detail: 'Token expired' }),
      })
      // Call 2: 401 on refresh
      .mockResolvedValueOnce({
        status: 401,
        ok: false,
        json: async () => ({ detail: 'Invalid refresh token' }),
      });

    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(apiFetch('/workflows')).rejects.toThrow('Session expired. Please log in again.');
    expect(getAccessToken()).toBeNull();
  });
});
