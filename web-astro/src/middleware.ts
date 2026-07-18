import { clerkMiddleware } from '@clerk/astro/server';

const PUBLIC_PATHS = ['/', '/sign-in', '/sign-up', '/sign-in/**', '/sign-up/**'];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => {
    if (p.endsWith('/**')) {
      return pathname.startsWith(p.slice(0, -3));
    }
    return pathname === p;
  });
}

export const onRequest = clerkMiddleware((auth, context, next) => {
  const url = new URL(context.request.url);
  const { pathname } = url;

  if (isPublicPath(pathname)) {
    return next();
  }

  try {
    const authObj = auth();
    console.log(`[middleware] ${pathname} isAuthenticated=${authObj.isAuthenticated}`);

    if (!authObj.isAuthenticated) {
      return authObj.redirectToSignIn({ returnBackUrl: url.pathname });
    }

    if (pathname.startsWith('/admin') && !authObj.has({ role: 'org:admin' })) {
      return context.redirect('/dashboard');
    }
  } catch {
    return context.redirect('/sign-in');
  }

  return next();
});
