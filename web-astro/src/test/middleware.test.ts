import { describe, test, expect, vi, beforeEach } from 'vitest';

vi.mock('@clerk/astro/server', () => ({
  clerkMiddleware: vi.fn((handler: any) => handler),
}));

const { onRequest } = await import('../middleware');

function makeCtx(pathname: string) {
  const redirectCapture = { url: '', status: 0 };
  return {
    request: { url: `http://localhost:4321${pathname}` },
    redirect: (url: string, status = 302) => {
      redirectCapture.url = url;
      redirectCapture.status = status;
      return new Response(null, { status, headers: { Location: url } });
    },
    _redirect: redirectCapture,
  } as any;
}

function makeAuthObj(opts: { isAuthenticated?: boolean; hasRole?: boolean } = {}) {
  const { isAuthenticated = true, hasRole = false } = opts;
  return {
    isAuthenticated,
    has: vi.fn(({ role }: { role: string }) => (role === 'org:admin' ? hasRole : false)),
    redirectToSignIn: vi.fn(({ returnBackUrl }: { returnBackUrl: string }) =>
      new Response(null, {
        status: 307,
        headers: { Location: `/sign-in?redirect_url=${encodeURIComponent(returnBackUrl)}` },
      }),
    ),
  };
}

describe('middleware enforcement', () => {
  test('public / passes through', async () => {
    const ctx = makeCtx('/');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('public /sign-in passes through', async () => {
    const ctx = makeCtx('/sign-in');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('public /sign-up passes through', async () => {
    const ctx = makeCtx('/sign-up');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('unauthenticated /dashboard → redirects to sign-in', async () => {
    const ctx = makeCtx('/dashboard');
    const next = vi.fn();
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    const res = await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.status).toBe(307);
    expect(res.headers.get('Location')).toContain('/sign-in');
  });

  test('unauthenticated /settings → redirects to sign-in', async () => {
    const ctx = makeCtx('/settings');
    const next = vi.fn();
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    const res = await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.status).toBe(307);
  });

  test('unauthenticated /admin → redirects to sign-in', async () => {
    const ctx = makeCtx('/admin');
    const next = vi.fn();
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    const res = await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.status).toBe(307);
  });

  test('unauthenticated /dashboard/sessions/abc → redirects to sign-in', async () => {
    const ctx = makeCtx('/dashboard/sessions/abc123');
    const next = vi.fn();
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: false }));

    const res = await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.status).toBe(307);
  });

  test('authenticated non-admin on /admin → redirects to /dashboard', async () => {
    const ctx = makeCtx('/admin');
    const next = vi.fn();
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: true, hasRole: false }));

    await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(ctx._redirect.url).toBe('/dashboard');
  });

  test('authenticated admin on /admin → passes through', async () => {
    const ctx = makeCtx('/admin');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: true, hasRole: true }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('authenticated user on /dashboard → passes through', async () => {
    const ctx = makeCtx('/dashboard');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: true }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('authenticated user on /settings → passes through', async () => {
    const ctx = makeCtx('/settings');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: true }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('authenticated user on /dashboard/sessions/xyz → passes through', async () => {
    const ctx = makeCtx('/dashboard/sessions/xyz789');
    const next = vi.fn(() => new Response('ok'));
    const authFn = vi.fn(() => makeAuthObj({ isAuthenticated: true }));

    await onRequest(authFn, ctx, next);
    expect(next).toHaveBeenCalled();
  });

  test('auth() throws → falls through to /sign-in', async () => {
    const ctx = makeCtx('/dashboard');
    const next = vi.fn();
    const authFn = vi.fn(() => { throw new Error('no keys'); });

    await onRequest(authFn, ctx, next);

    expect(next).not.toHaveBeenCalled();
    expect(ctx._redirect.url).toBe('/sign-in');
  });
});
