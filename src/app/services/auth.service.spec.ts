import { AUTH_EXPIRED_MESSAGE } from '../tools/aily-chat/services/http-error-handler.service';
import { AuthService } from './auth.service';

describe('AuthService auth expiry handling', () => {
  let service: any;

  beforeEach(() => {
    service = Object.create(AuthService.prototype) as any;
    service.authExpiredPromise = null;
  });

  it('deduplicates concurrent auth-expired handling', async () => {
    const logoutSpy = spyOn(service, 'logout').and.returnValue(Promise.resolve());

    const promiseA = service.handleAuthExpired();
    const promiseB = service.handleAuthExpired();

    const [errorA, errorB] = await Promise.all([promiseA, promiseB]);

    expect(logoutSpy).toHaveBeenCalledTimes(1);
    expect(errorA.message).toBe(AUTH_EXPIRED_MESSAGE);
    expect(errorB.message).toBe(AUTH_EXPIRED_MESSAGE);
  });

  it('passes through non-auth errors unchanged', async () => {
    const originalError = { status: 503, message: 'Service unavailable' };

    const result = await service.normalizeAuthError(originalError);

    expect(result).toBe(originalError);
  });
});
