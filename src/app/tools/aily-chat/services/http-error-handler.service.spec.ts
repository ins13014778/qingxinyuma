import { AUTH_EXPIRED_MESSAGE, isAuthenticationExpiredError } from './http-error-handler.service';

describe('http-error-handler authentication expiry', () => {
  it('returns true for HTTP 401 errors', () => {
    expect(isAuthenticationExpiredError({ status: 401 })).toBeTrue();
  });

  it('returns true for token expired messages', () => {
    expect(isAuthenticationExpiredError({ message: AUTH_EXPIRED_MESSAGE })).toBeTrue();
  });

  it('returns false for generic network failures', () => {
    expect(isAuthenticationExpiredError({ status: 503, message: 'Service unavailable' })).toBeFalse();
  });
});
