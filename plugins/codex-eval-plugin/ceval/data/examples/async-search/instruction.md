# Make live search reliable

Implement `createSearch({fetchResults, onState, delay = 100, timers})` in `search.cjs`, exported through CommonJS. `timers` supplies `setTimeout` and `clearTimeout`, defaulting to global timers. Return `{search(query), dispose()}`.

`search` trims its string query. For a nonempty query, immediately emit `{status:'loading', query, items:[]}`, debounce the fetch by `delay`, and invoke `fetchResults(query, {signal})` with an AbortSignal. On fulfillment emit `{status:'success',query,items:result}`; on non-abort failure emit `{status:'error',query,items:[],error:String(error.message || error)}`. Handle synchronous fetch throws as well as rejected promises.

Each new search cancels its pending timer, aborts any in-flight request, and invalidates all prior results immediately, even before the new debounce timer fires. A stale success or failure must never update state even if the transport ignores abort. Empty/whitespace query immediately emits `{status:'idle',query:'',items:[]}` without fetching. Repeating the same query is a new request, not a cache hit.

`dispose()` is idempotent, clears pending timers, aborts the current fetch, and prevents all future notifications and requests (including calls to `search` after disposal). Do not add dependencies. The controller must work headlessly; rendering a UI is out of scope.
