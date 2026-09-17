document.addEventListener('click', async event => {
  const button = event.target.closest('[data-seed-copy], [data-seed-link]');
  if (!button) return;
  const text = button.hasAttribute('data-seed-link') ? location.origin + location.pathname : button.dataset.seedCopy;
  const status = document.querySelector('#seed-copy-status');
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = button.hasAttribute('data-seed-link') ? '分享链接已复制，发给兄弟吧。' : '种子码已复制，大小写已保留。';
  } catch (_) {
    status.textContent = '无法自动复制，请长按或选中种子码复制。';
  }
  window.clearTimeout(window.seedCopyTimer);
  window.seedCopyTimer = window.setTimeout(() => { status.textContent = ''; }, 3500);
});
