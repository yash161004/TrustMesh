import { clerkMiddleware } from '@clerk/astro/server';

const protectedRoutes = ['/dashboard', '/settings', '/admin'];

export const onRequest = clerkMiddleware((auth, context, next) => {
  const url = new URL(context.request.url);
  const isProtectedRoute = protectedRoutes.some(route => url.pathname.startsWith(route));

  if (isProtectedRoute) {
    try {
      const authObj = auth();
      if (!authObj.isAuthenticated) {
        return authObj.redirectToSignIn({ returnBackUrl: url.pathname });
      }

      if (url.pathname.startsWith('/admin')) {
        const isAdmin = authObj.has({ role: 'org:admin' });
        if (!isAdmin) {
          return context.redirect('/dashboard', 302);
        }
      }
    } catch (err) {
      console.error("[MIDDLEWARE] Clerk Error:", err);
      return context.redirect('/sign-in', 302);
    }
  }

  return next();
});
