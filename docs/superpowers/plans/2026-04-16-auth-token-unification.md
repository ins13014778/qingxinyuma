# Auth Token Expiry Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一手写 `fetch`/SSE/子代理链路与 `HttpClient` 链路的登录失效处理，确保 token 过期时会清理登录态并返回一致提示。

**Architecture:** 在认证层增加一个可复用的“登录失效收口”能力，`authInterceptor` 与聊天/子代理直连链路都改为复用它。聊天错误归一化层补充认证失效识别，避免 UI 只收到局部报错而不触发全局登出。

**Tech Stack:** Angular 19, RxJS, Jasmine/Karma, Electron renderer services

---

### Task 1: Add Regression Coverage For Auth Expiry Detection

**Files:**
- Create: `src/app/tools/aily-chat/services/http-error-handler.service.spec.ts`
- Modify: `src/app/tools/aily-chat/services/http-error-handler.service.ts`

- [ ] **Step 1: Write failing tests for auth-expiry detection**

```typescript
import { isAuthenticationExpiredError } from './http-error-handler.service';

describe('isAuthenticationExpiredError', () => {
  it('returns true for HTTP 401 errors', () => {
    expect(isAuthenticationExpiredError({ status: 401 })).toBeTrue();
  });

  it('returns true for token-expired message text', () => {
    expect(isAuthenticationExpiredError({ message: 'Token已过期，请重新登录' })).toBeTrue();
  });

  it('returns false for generic network failures', () => {
    expect(isAuthenticationExpiredError({ status: 503, message: 'Service unavailable' })).toBeFalse();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx ng test --watch=false --browsers=ChromeHeadless --include src/app/tools/aily-chat/services/http-error-handler.service.spec.ts`
Expected: FAIL because `isAuthenticationExpiredError` does not exist yet.

- [ ] **Step 3: Implement the minimal detection helper**

```typescript
export function isAuthenticationExpiredError(err: any): boolean {
  const status = extractHttpStatusCode(err);
  if (status === 401) {
    return true;
  }

  const detail = extractErrorDetailMessage(err).toLowerCase();
  return /token.*过期|登录.*失效|重新登录|unauthorized/.test(detail);
}
```

- [ ] **Step 4: Re-run the targeted test**

Run: `npx ng test --watch=false --browsers=ChromeHeadless --include src/app/tools/aily-chat/services/http-error-handler.service.spec.ts`
Expected: PASS

### Task 2: Centralize Auth Expiry Handling

**Files:**
- Create: `src/app/services/auth.service.spec.ts`
- Modify: `src/app/services/auth.service.ts`
- Modify: `src/app/interceptors/auth.interceptor.ts`

- [ ] **Step 1: Write failing tests for the shared logout-on-expiry flow**

```typescript
describe('AuthService.handleAuthExpired', () => {
  it('logs out once and returns a normalized error', async () => {
    // spy on logout and assert duplicate calls share one in-flight promise
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx ng test --watch=false --browsers=ChromeHeadless --include src/app/services/auth.service.spec.ts`
Expected: FAIL because `handleAuthExpired` does not exist yet.

- [ ] **Step 3: Implement shared auth-expiry handling in AuthService**

```typescript
private authExpiredPromise: Promise<never> | null = null;

handleAuthExpired(message = 'Token已过期，请重新登录'): Promise<never> {
  if (!this.authExpiredPromise) {
    this.authExpiredPromise = this.logout()
      .catch(() => undefined)
      .then(() => Promise.reject(new Error(message)))
      .finally(() => { this.authExpiredPromise = null; });
  }
  return this.authExpiredPromise;
}
```

- [ ] **Step 4: Update authInterceptor to reuse the shared handler**

```typescript
return from(authService.handleAuthExpired()).pipe(
  switchMap(() => throwError(() => new Error('Token已过期，请重新登录')))
);
```

- [ ] **Step 5: Re-run the targeted auth service test**

Run: `npx ng test --watch=false --browsers=ChromeHeadless --include src/app/services/auth.service.spec.ts`
Expected: PASS

### Task 3: Wire Fetch/SSE/Subagent Paths Into Shared Auth Handling

**Files:**
- Modify: `src/app/tools/aily-chat/services/chat.service.ts`
- Modify: `src/app/services/background-agent.service.ts`
- Modify: `src/app/tools/aily-chat/services/subagent-session.service.ts`

- [ ] **Step 1: Add one helper per fetch-based service to normalize auth-expired failures**

```typescript
private async rethrowIfAuthExpired(error: any): Promise<never> {
  if (isAuthenticationExpiredError(error)) {
    return this.authService.handleAuthExpired();
  }
  throw error;
}
```

- [ ] **Step 2: Hook chat.service fetch/SSE error exits into the helper**

Run change in:
- `fetchContextInfo`
- `streamConnect`
- `chatRequest`

- [ ] **Step 3: Hook background-agent.service fetch errors into the helper**

Run change in:
- `processChatTurn`

- [ ] **Step 4: Hook subagent-session.service session creation / stream failures into the helper**

Run change in:
- `getOrCreateSession`
- `processSubagentChatTurn`

- [ ] **Step 5: Run focused verification**

Run: `npx ng test --watch=false --browsers=ChromeHeadless --include src/app/tools/aily-chat/services/http-error-handler.service.spec.ts --include src/app/services/auth.service.spec.ts`
Expected: PASS

- [ ] **Step 6: Run build-level verification**

Run: `npx ng build`
Expected: PASS
