exports.createSearch = ({fetchResults, onState, delay = 100, timers = globalThis}) => {
  let generation = 0, disposed = false, timer = null, controller = null;
  function cancel() {
    if (timer !== null) { timers.clearTimeout(timer); timer = null; }
    if (controller) { controller.abort(); controller = null; }
  }
  return {
    search(raw) {
      if (disposed) return;
      const mine = ++generation;
      cancel();
      const query = raw.trim();
      if (!query) { onState({status:'idle',query:'',items:[]}); return; }
      onState({status:'loading',query,items:[]});
      timer = timers.setTimeout(async () => {
        timer = null;
        const current = new AbortController();
        controller = current;
        try {
          const items = await fetchResults(query, {signal:current.signal});
          if (!disposed && mine === generation) onState({status:'success',query,items});
        } catch (e) {
          if (!disposed && mine === generation && e?.name !== 'AbortError')
            onState({status:'error',query,items:[],error:String(e?.message || e)});
        }
      }, delay);
    },
    dispose() { if (!disposed) { disposed = true; ++generation; cancel(); } }
  };
};
