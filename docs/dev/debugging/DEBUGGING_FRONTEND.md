# Debugging Frontend

## 0. Symptom

An **example** (loading screen being stuck):
* URL: `/` (Latest tab highlighted ✅)
* UI: `Loading latest StageEpisode…` forever
* No error message, no episode header, no timeline.
What this means:
* Router is rendering `LatestEpisodeView`.
* Something inside that component (or its hook) is never leaving the “loading” branch.

---

## 1. Confirm the routing stack
Files to check
* `ui-stage/src/main.tsx`
```tsx
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  </StrictMode>,
)
```
* `ui-stage/src/AppRouter.tsx`
```tsx
<Routes>
  <Route path="/" element={<AppShell />}>
    <Route index element={<LatestEpisodeView />} />
    <Route path="episodes" element={<EpisodesListPlaceholder />} />
    ...
  </Route>
</Routes>
```
**Checklist**
* `BrowserRouter` wraps `AppRouter`.
* `/` has an `index` route pointing to `LatestEpisodeView`.
* Nav clicks change the URL path in the address bar.

If all of this looks right and the URL changes as expected, the router is probably fine and you move down a layer.

---

## 2. Check which component owns the “loading” UI

In our example case:
* `LatestEpisodeView` decides what to show based on `episode`, `error`, and `isLoading` from `useEpisodeLoader`.
```tsx
const { episode, error, isLoading } = useEpisodeLoader();

if (error) { ... }

if (!episode) {
  if (isLoading) return <div className="loading">Loading…</div>;
return <div className="empty">No episode available.</div>;
}
```
So if you’re stuck on “Loading…”, one of these is true:
* `isLoading` is never flipped to false, or
* `episode` is never set, so you’re stuck in the `!episode` branch.

At this point, router is not the main suspect anymore — `useEpisodeLoader` is.

---

## 3. Instrument the loader hook (what we did)
We added logging to `useEpisodeLoader`:
```tsx
console.log("loader start", { episode, error, isLoading });

useEffect(() => {
  console.log("fetching…");

  try {
    const raw = await getLatestEpisode();
    const vm = buildEpisodeView(raw as any);

    if (ignoreRef.current) return;
    console.log("setting episode", vm);
    setEpisode(vm);
    setError(null);
  } catch (err) {
    if (ignoreRef.current) return;
    console.log("error caught", err);
    ...
  } finally {
    if (ignoreRef.current) return;
    setIsLoading(false);
    console.log("finally: setting isLoading=false");
  }
}, []);
```
Then we watched the console:
1. `loader start { episode: null, error: null, isLoading: true }`
2. `fetching…`
3. `setting episode { … }`
4. `finally: setting isLoading=false`
5. `Render LatestEpisodeView { episode: {...}, error: null, isLoading: false }`

Once you see **both** `setting episode` and `finally: setting isLoading=false`, you know:
* The fetch succeeded.
* State setters ran.
* The component re-rendered with updated state.

If _those_ logs show up but the UI still shows “Loading…”, then you’d suspect the conditional rendering in `LatestEpisodeView`.

If **only** `finally: setting isLoading=false` shows up (no “setting episode”), you’d suspect:
* Bad response shape
* `buildEpisodeView` throwing
* Or the episode being `null` / undefined

---

## 4. The real culprit: StrictMode + stale effect run

The original version used this pattern:
```tsx
const startedRef = useRef(false);

useEffect(() => {
  if (startedRef.current) return;
  startedRef.current = true;

  let isActive = true;
  (async () => {
    const raw = await getLatestEpisode();
    ...
    if (!isActive) return;
    setEpisode(vm);
    ...
  })();

  return () => { isActive = false; };
}, []);
```

Under React **StrictMode**, effects can run twice in dev to catch unsafe patterns. That means:
1. First effect run kicks off a fetch.
2. Cleanup runs → `isActive = false`.
3. Second effect run decides “already started” (because of `startedRef`) → doesn’t fetch, but we still keep the _first_ async fetch in flight.
4. When that first fetch resolves, isActive is already false, so it skips setEpisode, but still hits setIsLoading(false) in finally.

You end up with:
* `episode` still `null`
* `isLoading` is `false`
* UI stuck in “no episode + isLoading” logic or generally in an unexpected branch.

---

## 5. The fix we landed on

Final `useEpisodeLoader`:
```tsx
export function useEpisodeLoader(): UseEpisodeLoaderResult {
const [episode, setEpisode] = useState<EpisodeViewModel | null>(null);
const [error, setError] = useState<string | null>(null);
const [isLoading, setIsLoading] = useState<boolean>(true);

// This ref marks whether *this effect run* should be ignored
const ignoreRef = useRef(false);

console.log("loader start", { episode, error, isLoading });

useEffect(() => {
ignoreRef.current = false;      // this effect run is active
setIsLoading(true);

    (async () => {
      console.log("fetching…");

      try {
        const raw = await getLatestEpisode();
        const vm = buildEpisodeView(raw as any);

        if (ignoreRef.current) return;

        console.log("setting episode", vm);
        setEpisode(vm);
        setError(null);
      } catch (err: unknown) {
        if (ignoreRef.current) return;

        const msg = err instanceof Error ? err.message : "Unknown error";
        console.log("error caught", err);

        setEpisode(null);
        setError(msg);
      } finally {
        if (ignoreRef.current) return;

        setIsLoading(false);
        console.log("finally: setting isLoading=false");
      }
    })();

    return () => {
      // If this effect run is being torn down, mark its async work as ignored
      ignoreRef.current = true;
    };
}, []);

return { episode, error, isLoading };
}
```

Key ideas:
* **One source of truth** for “should this async run still write to state?” → `ignoreRef.current`.
* We **don’t** short-circuit effects with a `startedRef`; we just ignore stale runs.
* StrictMode double-execution is safe: the second run’s cleanup will flip `ignoreRef.current` for that run, but the current active run stays valid.

---

## 6. Updated “Router + Loader” debugging checklist

When you see “Loading…” forever:
**1. Verify router structure**
* `BrowserRouter` wraps `AppRouter` in `main.tsx`.
* Routes in `AppRouter.tsx` look sane.
* URL changes when you click nav items.
**2. Confirm which component renders the loading UI**
* Search for `"Loading latest StageEpisode"` and see which component (here `LatestEpisodeView`) owns that branch.
**3. Instrument the data loader hook**
* Add `console.log` around:
  * Initial state
  * Before fetch
  * After successful fetch
  * In `catch`
  * In `finally`
* Check DevTools console to see if:
  * Fetch is called
  * Episode is set
  * `isLoading` flips
**4. Check for StrictMode double effects**
* If you see your effect’s logs twice on mount, assume StrictMode is doing its thing.
* Avoid patterns like `startedRef` + local `isActive` flags that can get out of sync.
**5. Use an `ignoreRef` pattern for async effects**
* Single `useRef` that marks “this effect run is stale, don’t touch state from here.”
**6. Re-run tests and make sure they cover edge cases**
* We added `LatestEpisodeView.loading.test.tsx` to explicitly test:
  * `isLoading=true, episode=null` → shows loading
  * `isLoading=false, episode=null` → shows empty state
  * `isLoading=false, episode!=null` → renders content, no loading text