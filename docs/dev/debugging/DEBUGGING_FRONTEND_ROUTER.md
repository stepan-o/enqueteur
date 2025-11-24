# Debugging Frontend Router

## 0. Mental model: what are we debugging, exactly?

For this app, the stack is:

```
main.tsx  
    → BrowserRouter  
        → AppRouter  
            → AppShell  
                → <Outlet/>  
                    → LatestEpisodeView
```

Plus:

`LatestEpisodeView → useEpisodeLoader() → setEpisode()`

> There should be **no other App component** in the tree.

Example bug (loading freeze in `LatestEpisodeView`, described in docs/dev/debugging/DEBUGGING_LOADING_SCREEN.md):
* **Hook clearly updates state** (we checked the debug logs from the loading screen first: `episode` is set, `isLoading` becomes `false`)
* UI **stays** on `Loading latest StageEpisode…`

So somewhere on this path, re-renders are not flowing through properly.

We want to answer:
> “When episode changes in the hook, **which component is the last one that actually re-renders?**”

That’s the whole router-debug game.

---

## 1. First line of defense: “render logs” at each layer

Add **temporary `console.log` calls** at every level in the route tree to see who actually re-renders when the episode arrives.

### a) In `LatestEpisodeView.tsx`

Right after the hook:

```ts
export default function LatestEpisodeView() {
  const { episode, error, isLoading } = useEpisodeLoader();
  console.log("Render LatestEpisodeView", { episode, error, isLoading });
  ...
}
```

What to look for:
* On initial load: you should see `episode: null, isLoading: true`
* After fetch: you should see `episode: {…}, isLoading: false`

If that second log **never appears**, something above is blocking the re-render (or the component was unmounted).

---

### b) In `AppShell.tsx` (the layout that wraps your routes)

Add:
```tsx
export default function AppShell() {
  console.log("Render AppShell");
  return (
    <div className={styles.shell}>
      ...
    </div>
  );
}
```

If AppShell never logs again after load, then:
* Router might have mounted it once and never updated
* Or `<Outlet />` children changed while AppShell remained static (that’s okay) — but we still confirm.

---

### c) In `AppRouter.tsx`

Add:
```tsx
  export default function AppRouter() {
  console.log("Render AppRouter");
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<LatestEpisodeView />} />
        ...
      </Route>
    </Routes>
  );
}
```

If AppRouter only logs once, that’s normal – but we want to know it’s in the path and not accidentally wrapped in something weird.

---

### d) In `main.tsx`

Whatever your root looks like, log there too:

```tsx
export default function App() {
  console.log("Render App");
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}
```

> **Goal:** When the episode is fetched, you should at least see a new `Render LatestEpisodeView` line.
If you don’t, the issue is above `LatestEpisodeView` (router/layout).

---

## 2. Verify the route wiring

Double-check your route tree matches your mental model.

You previously had something like:
```tsx
// AppRouter.tsx
import { Routes, Route } from "react-router-dom";
import AppShell from "./AppShell";
import LatestEpisodeView from "./routes/LatestEpisodeView";
import EpisodesListPlaceholder from "./routes/EpisodesListPlaceholder";
import AgentsPlaceholder from "./routes/AgentsPlaceholder";
import SettingsPlaceholder from "./routes/SettingsPlaceholder";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<LatestEpisodeView />} />
        <Route path="episodes" element={<EpisodesListPlaceholder />} />
        <Route path="agents" element={<AgentsPlaceholder />} />
        <Route path="settings" element={<SettingsPlaceholder />} />
      </Route>
    </Routes>
  );
}
```

Checklist here:
* There’s exactly one `<Routes>` tree.
* `LatestEpisodeView` is indeed the `index` route under `/`.
* `AppShell` contains `<Outlet />`:
```tsx
<main className={styles.main}>
  <Outlet />
</main>
```

If `<Outlet />` is missing or incorrectly placed, your route content never renders (or renders somewhere off-screen).

---

## 3. Confirm the router providers in `main.tsx`

You should have **exactly one** `<BrowserRouter>` at the root:

```tsx
import { BrowserRouter } from "react-router-dom";
import AppRouter from "./AppRouter";

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}
```

Pitfalls to watch for:
* **Multiple routers** (e.g., wrapping AppShell again with a `BrowserRouter` or `MemoryRouter`) – this can isolate parts of the tree and mess up navigation.
* Using a router only in tests (`MemoryRouter`) but not in the real app.

---

## 4. Connect hook behavior to route behavior

Now that your `useEpisodeLoader` has logs:
```ts
console.log("loader start", { episode, error, isLoading });
console.log("fetching…");
console.log("setting episode", vm);
console.log("error caught", err);
console.log("finally: setting isLoading=false");
```

Combine that with `Render LatestEpisodeView` logs:

If you see:
```text
loader start { episode: null, error: null, isLoading: true }
fetching…
setting episode { … }
finally: setting isLoading=false
```

**but no new** `Render LatestEpisodeView { episode: {…}, isLoading: false }`
* The hook updated state, but React didn’t re-render this component → router/layout bug.
* If you do see:
```text
Render LatestEpisodeView { episode: {…}, isLoading: false }
```
but the UI still shows “Loading latest StageEpisode…”
* Something else is accidentally rendering a **second copy** of `LatestEpisodeView` somewhere (or the markup in the DOM you’re seeing is from an _earlier_ render).

In that case, check:
* You’re not rendering `LatestEpisodeView` twice in different routes.
* You don’t have an older version of the app still mounted (Vite dev server usually hot-reloads, but sometimes a stale tab lingers).

---

## 5. Use React DevTools (when you feel ready)

When you install React DevTools (Chrome/Firefox extension), you’ll be able to:
* Click the `LatestEpisodeView` component in the Components panel.
* Inspect its **props and hooks** live.
* See `useEpisodeLoader` state values (`episode`, `isLoading`) at that exact moment.

This gives you a visual:
> “React thinks this component is in state X, but my DOM is still showing Y.”

Which is a huge clue whether it’s:
* A **state problem** (hook not updating), or
* A **routing / layout / stale-render** problem.

For your current bug, the logs already tell us it’s the second category.

---

## 6. Quick router-debug checklist you can reuse

When “UI is stuck on old state” and you’re using React Router:
**1. Log renders**
* Add `console.log("Render X", …)` to the route component and layout.
**2. Watch for re-renders**
* Does the route component re-log after state changes? If not → router/layout control.
3. Verify `<Outlet />`
* Make sure your parent route renders `<Outlet />` exactly once in the right place.
4. Check route config
* `index` vs `path="/"` vs nesting mistakes.
5. Confirm single router
* One `<BrowserRouter>` at the top, no extra routers inside.
6. Compare test router vs app router
* Tests may use `MemoryRouter` and not show runtime issues that appear with `BrowserRouter`.