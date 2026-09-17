(() => {
  const welcome = document.querySelector('[data-visitor-welcome]');
  if (!welcome) return;
  const count = async () => {
    try {
      const response = await fetch(welcome.dataset.endpoint, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: {'X-CSRFToken': welcome.dataset.csrf, 'Accept': 'application/json'},
        signal: AbortSignal.timeout(8000)
      });
      if (!response.ok || response.status === 204) return;
      const data = await response.json();
      if (!Number.isSafeInteger(data.visitor_number) || data.visitor_number < 1 ||
          !Number.isSafeInteger(data.total_visitors) || data.total_visitors < 1) return;
      welcome.querySelector('[data-visitor-greeting]').textContent = `欢迎你，第${data.visitor_number}位好兄弟`;
      welcome.querySelector('[data-visitor-total]').textContent = `已有 ${data.total_visitors} 位兄弟来过`;
    } catch (_) {
      // Counting must never interrupt browsing or replace content with an error.
    }
  };
  // Serialize first-time requests across tabs where the browser supports it so
  // the second tab receives the signed cookie issued for the first tab.
  if (navigator.locks) navigator.locks.request('bbmod-visitor', count).catch(() => {});
  else count();
})();
