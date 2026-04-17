import { inject } from '@angular/core';
import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { Observable, catchError, from, switchMap, throwError } from 'rxjs';
import { API } from '../configs/api.config';
import { AuthService } from '../services/auth.service';
import { AUTH_EXPIRED_MESSAGE } from '../tools/aily-chat/services/http-error-handler.service';

function shouldInterceptRequest(url: string): boolean {
  const apiUrls = Object.values(API);
  return apiUrls.some(apiUrl => url.startsWith(apiUrl));
}

function shouldSkipAuth(request: HttpRequest<any>): boolean {
  return request.headers.has('X-Skip-Auth');
}

function shouldHandleUnauthorized(req: HttpRequest<any>, error: HttpErrorResponse): boolean {
  if (error.status !== 401) {
    return false;
  }

  return !req.url.includes('auth/login');
}

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> => {
  const authService = inject(AuthService);

  if (!shouldInterceptRequest(req.url)) {
    return next(req);
  }

  if (shouldSkipAuth(req)) {
    return next(req.clone({
      headers: req.headers.delete('X-Skip-Auth')
    }));
  }

  return from(addTokenHeader(req, authService)).pipe(
    switchMap(request => next(request)),
    catchError(error => {
      if (error instanceof HttpErrorResponse && shouldHandleUnauthorized(req, error)) {
        return from(authService.handleAuthExpired(AUTH_EXPIRED_MESSAGE)).pipe(
          switchMap(authError => throwError(() => authError))
        );
      }

      return throwError(() => error);
    })
  );
};

async function addTokenHeader(request: HttpRequest<any>, authService: AuthService, token?: string | null): Promise<HttpRequest<any>> {
  if (!token) {
    token = await authService.getToken2();
  }

  if (!token) {
    return request;
  }

  return request.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });
}
