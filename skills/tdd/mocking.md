# When to Mock

Prefer mocks at **system boundaries** where a real dependency would make a test slow, nondeterministic, or dependent on an external service:

- External APIs (payment, email, etc.)
- Databases (sometimes - prefer test DB)
- Time/randomness
- File system (sometimes)

Avoid mocking:

- Your own classes/modules
- Internal collaborators
- Anything you control

## Keep the behavior under test real

A mock replaces behavior. Do not mock the function or dependency whose behavior the test claims to verify. For each mock, state which boundary it isolates and assert the resulting caller-visible value, state, exception, or side effect; a mock-call assertion alone does not prove that behavior.

Use a real lightweight implementation or focused fake when it can verify more of the contract deterministically. For example, if the behavior under test includes database mapping or transaction semantics, prefer the project's test database over a mock of the repository. Mocks are still useful for controlling external success and failure responses.

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific functions for each external operation instead of one generic function with conditional logic:

```typescript
// GOOD: Each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: Mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK approach means:
- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint
