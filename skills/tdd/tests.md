# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test
- Has an oracle that rejects a realistic wrong behavior
- Derives expected behavior independently of the implementation
- Awaits asynchronous work and critical assertions

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```typescript
// BAD: Tests implementation details
test("checkout calls paymentService.process", async () => {
  const mockPayment = { process: jest.fn() };
  // Illustrative: checkout receives its payment collaborator through injection.
  await checkout(cart, payment, mockPayment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

The example uses a valid Jest mock function, but remains a bad test because it verifies an internal interaction instead of checkout behavior. Prefer asserting the resulting order/payment outcome through the public interface. Confirm framework methods and signatures against the project's installed version and imports; do not infer an API from a plausible name.

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

These are review signals, not automatic verdicts. For each test, identify the concrete wrong behavior it should reject. A syntax pattern alone does not prove that a test is weak.

**Weak oracle**: checking only existence, truthiness, type, no exception, or status when the contract defines stronger behavior.

```typescript
// WEAK: many incorrect totals are still truthy
expect(calculateTotal(items)).toBeTruthy();

// STRONGER: fails if the calculation returns the wrong total
expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
```

For every new test, think of one small realistic production defect (for example, dropping one item from a total or mapping the wrong field). Keep the test only when its meaningful assertion would fail for that defect. Avoid duplicate scenarios that add no distinct behavioral check.

For async tests, await the operation and the framework's async assertion. Ensure a failure cannot be swallowed or skipped by a branch; otherwise the test may report green without checking its claim.

```typescript
// BAD: Bypasses interface to verify
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: Verifies through interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```typescript
// BAD: Expected value is recomputed the way the code computes it
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// GOOD: Expected value is an independent, known literal
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
