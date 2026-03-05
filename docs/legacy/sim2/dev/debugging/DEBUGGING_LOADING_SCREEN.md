# How to investigate loading screen getting stuck

🚨 If your UI is still stuck on “Loading latest StageEpisode…”

Here’s what you should check based on which logs appear.

We must determine **where the loading state is getting stuck.**

## Step 0 — Add temporary console logs to `useEpisodeLoader()`

### 0.1 Logging the initial state
Add this inside the hook:
```ts
console.log("loader start", { episode, error, isLoading });
```
This fires on **every render of the hook**, which helps you see:
* whether the hook mounts at all
* whether isLoading ever starts as `true`
* whether episode ever changes

---

### 0.2 Logging before the fetch begins
Add this inside the async block:
```ts
console.log("fetching…");
```
This tells you:
* your effect ran
* the hook entered the async fetch
* the fetch wasn’t skipped by `startedRef.current`

If you **don’t** see this, the hook is not entering the fetching phase — which is a massive clue.

---

### 0.3 Logging after successful fetch
Add this after successful fetch:
```ts
console.log("setting episode", vm);
```
This will tell you:
* The fetch succeeded
* Data was received
* The VM was built correctly
* The state setter is being reached

If this line **does not appear**, the freeze is happening before the VM is created.

---

### 0.4 Logging on error
Add this inside catch:
```ts
console.log("error caught", err);
```
This will reveal:
* network failures
* backend API failures
* CORS issues
* JSON-parsing failures
* environment variable issues

If the fetch is failing silently, this will expose it.

---

### 0.5 Logging when loading finishes
Inside finally:
```ts
console.log("finally: setting isLoading=false");
```
You should **always** see this, regardless of success or failure.

If this line **never appears**, then:
* the fetch promise is hanging forever
* the code never exits the await
* the backend might not be responding
* or the fetch is waiting on a blocked port / CORS issue

This explains a “permanent loading” screen.

### 0.6 Reload the page and check the console  
Make sure you’re running the app

In your project root:
```bash
npm run dev
```

Open the app in the browser (likely):

> http://localhost:5173/

Open the page in Chrome → Right-click → Inspect → Go to the Console tab.

Refresh the page (⌘R / Ctrl+R).

We’ll do everything from here.  
Your console output will tell us exactly where it's stuck.

## 1. Diagnosing the loading freeze

🚨 If your UI is still stuck on “Loading latest StageEpisode…”

Here’s what you should check based on which logs appear:

### Case A — You DO NOT see “fetching…”
* Your effect is not running
* `useEpisodeLoader()` is never mounting
* or `startedRef.current` is stuck on `true`
* or the file path/integration broke after refactor

### Case B — You see “fetching…” but NOTHING after
* The `await getLatestEpisode()` call never resolves

This is the most likely cause of your loading freeze.

Check:
* Does the server actually return the latest episode?
* Is the backend running on http://127.0.0.1:8000?
* Does `VITE_API_BASE_URL` resolve correctly?
* Do you see the request in the Network tab?
* Does the endpoint hang forever?

### Case C — You see “error caught …”
* Your fetch is failing fast
* The loader returns `error`
* But your UI still shows “Loading…”
* That means `episode` is `null` AND `isLoading` is `true`

This would imply the `finally` block never ran (bad) OR `isLoading` was overwritten somewhere else (unlikely with this code).

### Case D — You see “finally: setting isLoading=false”
…but the UI still shows the loading screen?
* Then the UI logic is wrong
* Or episode never becomes non-null
* Or the new conditional accidentally broke the logic:
```ts
if (!episode) {
  if (isLoading) return ...
  return "No episode"
}
```

If `isLoading=false` AND `episode=null`, the UI will ALWAYS show:

No episode available.

But you're seeing the loading screen, not the empty screen, which means:

`isLoading` is never flipping to false.  
→ That leads right back to Case B.

## 2. What you should _ideally_ see

On a healthy load, you’d expect something like:
1. `loader start { episode: null, error: null, isLoading: true }`
2. `fetching…`
3. `setting episode { ... }`
4. `finally: setting isLoading=false`
5. Another `loader start` with something like  
`{ episode: {…}, error: null, isLoading: false }`

At that point, the UI should leave the loading state and render the episode.

---

## 3. Use this decision tree

Watch which logs appear and then follow the matching branch.

### 🔴 Case A — You never see fetching…

**What you see:**
* `loader start …` maybe
* No `fetching…`

**What it means:**
* `useEpisodeLoader` mounted, but `useEffect` early-returned
  * `startedRef.current` was already `true`, or
  * the effect never ran at all

**What to do:**
1. Confirm `useEpisodeLoader` is really being called:
```ts
// in LatestEpisodeView.tsx just above `const { episode… }`
console.log("LatestEpisodeView render");
```

2. If that prints, check in `useEpisodeLoader`:
* Add:
```ts
console.log("inside useEffect, startedRef.current =", startedRef.current);
```
right inside the `useEffect` before the `if`:
```ts
useEffect(() => {
  console.log("inside useEffect, startedRef.current =", startedRef.current);
  if (startedRef.current) return;
  startedRef.current = true;
  ...
}, []);
```

If `startedRef.current` is `true` on first run, something weird is happening (e.g. hot reload or a double mount). For now you can temporarily remove the guard to see if that’s the culprit:
```ts
// TEMP for debugging – comment this out:
// if (startedRef.current) return;
// startedRef.current = true;
```
Reload and see if fetching… appears.

---

### 🟠 Case B — You see fetching… but nothing after that
**What you see:**
* `loader start …`
* `fetching…`
* Then no `setting episode`
* No `error caught`
* No `finally: setting isLoading=false`

**What it means:**

The code is stuck on:
```ts
const raw = await getLatestEpisode();
```

**What it means:**
* The fetch promise never resolves/rejects
* The backend isn’t responding or hanging

**How to confirm (Network tab):**
1. In DevTools, go to **Network** tab.
2. Clear the log (trash icon).
3. Refresh the page.
4. Look for a request to something like `/episodes/latest` (whatever `getLatestEpisode` calls).
5. Check:
* **Status:**
  * `200` → OK (then we should see more logs; if we don’t, the bug is inside `getJson`)
  * `(pending)` forever → backend hanging
  * `CORS error` / `blocked` → browser is blocking it
* **URL:** is it hitting `http://127.0.0.1:8000/...` or some wrong base URL?

If it’s stuck pending or failing, the loading freeze is because the **backend** never answers, not the React logic.

Optional extra log inside `getJson` to see the URL and status:
```ts
console.log("GET", url);
...
console.log("response status", res.status);
```

### 🟡 Case C — You see `error caught …` and `finally: setting isLoading=false`
**What you see:**
* `loader start …`
* `fetching…`
* `error caught Error: HTTP 500 …` (for example)
* `finally: setting isLoading=false`
* Then a new `loader start` with  
`{ episode: null, error: "HTTP …", isLoading: false }`

**What it means:**
* Backend responded with an error
* Hook set error
* isLoading correctly flipped to false

But your UI logic:
```tsx
if (error) {
  return <div className="error">Error loading episode: {error}</div>;
}
if (!episode) {
  if (isLoading) {
    return <div className="loading">Loading latest StageEpisode…</div>;
  }
  return <div className="empty">No episode available.</div>;
}
```

should show the **error** state, not the loading one.
If you still see “Loading…”, then `isLoading` is somehow still `true` (which would mean the `finally` never ran → back to Case B).

---

### 🟢 Case D — You see `setting episode` and `finally: setting isLoading=false`
**What you see:**
* `loader start {…, isLoading: true}`
* `fetching…`
* `setting episode { id: "…", ... }`
* `finally: setting isLoading=false`
* Then a new `loader start { episode: {…}, isLoading: false }`

**What it means:**
* Data load is fine.
* Hook state is correct.
* If the UI still shows “Loading…”, then the problem is:
  * You’re somehow seeing a stale build (browser cache / dev server old build), or
  * Another component is still rendering its own loading text, or
  * The `LatestEpisodeView` you’re editing is not the one actually used in the router.

**Things to check:**
1. Hard reload: ⌘⇧R / Ctrl+Shift+R.
2. Add a unique marker in the JSX:
```tsx
return (
  <div>
    <div>DEBUG: LatestEpisodeView v2</div>
    ...
  </div>
);
```

If that text doesn’t show, you’re editing the wrong file / wrong route.

## 4. Quick checklist you can follow
1. **Reload page with DevTools open.**
2. **Note which logs appear and in what order.**
3. Go to **Network tab**, check the API request status.
4. Use the decision tree:
* No `fetching…` → effect not running (or early return).
* `fetching…` only → backend request is hanging.
* `error caught` + `finally` → backend error, UI should show error.
* `setting episode` + `finally` → hook is fine, check route/wiring/caching.

## 5. Example

### 5.1 The hook ran twice at the beginning — expected

```
loader start { episode: null, error: null, isLoading: true }
loader start { episode: null, error: null, isLoading: true }
```

This happens because React Strict Mode in development intentionally double-invokes effects only during DEV to catch side-effects.

👉 This is normal, not a bug.  
Our logic guards against it using:

```ts
if (startedRef.current) return;
```

So fetch only runs once.

---

### 5.2 The fetch DID run

You see:
```
fetching…
```

This logs from inside the async IIFE inside `useEffect`.

👉 This means `getLatestEpisode()` **_was_ executed.**

---

### 5.3 The episode WAS successfully fetched

You see:
```
setting episode ▶ Object
```

This tells us:
* the fetch returned successfully
* `buildEpisodeView()` produced a valid EpisodeViewModel
* `setEpisode(vm)` was called

**🚨 IMPORTANT**

If `setEpisode(vm)` runs, React will **re-render** `LatestEpisodeView`, this time with `episode != null`.

### 5.4 After everything, `isLoading` is set to false

You see:
```
finally: setting isLoading=false
```

So the state becomes:
```
episode = <Object>
error = null
isLoading = false
```

At this point:

LatestEpisodeView’s conditional code:
```tsx
if (!episode) {
  if (isLoading) return <div>Loading...</div>;
  return <div>No episode</div>;
}
```

should _skip_ this whole block, because:
* `episode !== null`
* `isLoading === false`

Meaning — the UI should show the full episode.

But it doesn’t.

### 5.5 This means the problem is not the hook — it’s REACT ROUTER

The warnings in your screenshot are NOT harmless.

You see these:
```
React Router Future Flag Warning: React Router will begin wrapping state updates...
React Router Future Flag Warning: Relative route resolution...
```

These come from your AppShell navigation layout and are common when:
* a route is mounted twice
* a route is wrapped in Suspense
* the route tree is wrong
* the element never updates because the parent layout never re-renders

**⚠️ Translation: your component updates its internal state, but React Router is NOT remounting or re-rendering the route.**

Your UI is frozen on the initial render because the **component tree above it** is blocking updates.

### 5.6 🎯 How we know Router is the cause
#### 🔍 5.6.1 The hook logs prove:
* State updated fine
* Episode is now non-null
* isLoading is false
  * So your rendered UI _should_ change.

#### 🔍 5.6.2 The new episode never appears on screen
That means **the component did not re-render**, even when state changed.

#### 🔍 5.6.3 React Router warnings appear at the exact moment state updates occur

> useEpisodeLoader.ts:29—fetching…
> installHook.js:1—⚠️ React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7. You can use the `v7_startTransition` future flag to opt-in early. For more information, see https://reactrouter.com/v6/upgrading/future#v7_starttransition.

That indicates React Router is interfering with React’s rendering cycle.

#### 🔍 5.6.4 The freeze only happens in LatestEpisodeView, not in tests

Tests bypass React Router entirely.

👉 Therefore, the bug is in the routing layer, not in your hook.

### 5.7 What could cause this? (These are VERY common)

#### Option 1 — LatestEpisodeView is wrapped inside a memoized layout
Example:
```tsx
<Outlet />
```

inside a parent component that:
* has no reactive props
* is never re-rendered
* traps its children behind a stale reference

#### Option 2 — The <Routes> tree is incorrectly nested
Sometimes a route is “static” because the parent route is not allowing re-renders.

#### Option 3 — StrictMode double render is conflicting with fetch call
In rare cases, an antipattern in useEpisodeLoader may be caught by StrictMode behavior.

#### Option 4 — The route is rendered in a container with CSS that hides overflow
Less likely, but seen before.

See docs/dev/debugging/DEBUGGING_FRONTEND_ROUTER.md for more info.