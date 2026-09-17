'use strict';
document.querySelectorAll('[data-confirm]').forEach(button => button.addEventListener('click', event => {
  if (!window.confirm(button.dataset.confirm)) event.preventDefault();
}));
document.querySelectorAll('[data-copy], [data-copy-origin]').forEach(button => button.addEventListener('click', async () => {
  const value = button.hasAttribute('data-copy-origin') ? window.location.origin : button.dataset.copy;
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(value);
    else {
      const field = document.createElement('textarea'); field.value = value; document.body.appendChild(field);
      field.select(); const ok = document.execCommand('copy'); field.remove(); if (!ok) throw new Error('copy');
    }
    const old = button.textContent; button.textContent = '已复制'; setTimeout(() => button.textContent = old, 1800);
  } catch { window.prompt('复制下面的内容：', value); }
}));
document.querySelectorAll('[data-upload]').forEach(form => form.addEventListener('submit', () => {
  if (!form.checkValidity()) return;
  const button = form.querySelector('button[type="submit"], button:not([type])');
  if (button) { button.disabled = true; button.textContent = '正在上传并检查…'; }
  form.querySelector('.upload-status').textContent = '上传期间请保持页面打开。文件较大时需要一些时间。';
}));
