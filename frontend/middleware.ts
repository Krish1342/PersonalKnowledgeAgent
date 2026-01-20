import { authMiddleware } from '@clerk/nextjs';

export default authMiddleware({
  // Only landing page and auth routes are public
  // All other routes require authentication
  publicRoutes: [
    '/', // Landing page only
    '/sign-in(.*)',
    '/sign-up(.*)',
    '/api/health(.*)',
  ],
  
  // Routes that can always be accessed
  ignoredRoutes: [
    '/api/health',
  ],
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
