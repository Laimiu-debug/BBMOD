'use strict';
function bindPage(root = document) {
root.querySelectorAll('[data-confirm]').forEach(button => button.addEventListener('click', event => {
  if (!window.confirm(button.dataset.confirm)) event.preventDefault();
}));
root.querySelectorAll('[data-copy], [data-copy-origin]').forEach(button => button.addEventListener('click', async () => {
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
root.querySelectorAll('[data-upload]').forEach(form => {
  form.querySelectorAll('input:not([type=file]), textarea').forEach(input => {
    input.addEventListener('input', () => { input.dataset.edited = 'true'; });
  });
  const autofill = (name, value) => {
    const input = form.elements.namedItem(name);
    if (!input || !value || input.dataset.edited) return;
    if (!input.value || input.value === input.dataset.autofilled || (name === 'version' && input.value === '1.0.0')) {
      input.value = value; input.dataset.autofilled = value;
    }
  };
  form.querySelectorAll('[data-drop-zone]').forEach(zone => {
    const input = zone.querySelector('input[type=file]');
    const summary = zone.querySelector('[data-file-summary]');
    const selected = () => {
      const file = input.files[0];
      input.setCustomValidity(''); zone.classList.remove('invalid');
      if (!file) { summary.textContent = '尚未选择文件'; return; }
      const suffix = input.accept.toLowerCase();
      const problem = !file.name.toLowerCase().endsWith(suffix) ? `请选择 ${suffix.toUpperCase()} 文件。` :
        file.size > Number(zone.dataset.maxBytes) ? '文件超过大小限制，请选择较小的文件。' : '';
      input.setCustomValidity(problem);
      zone.classList.toggle('invalid', Boolean(problem));
      summary.textContent = problem || `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
      if (problem) return;
      const stem = file.name.replace(/\.(exe|zip)$/i, '');
      const version = stem.match(/(?:^|[_ -])v?(\d+\.\d+\.\d+(?:-[A-Za-z][A-Za-z0-9-]*(?:\.\d+)*)?)$/i);
      if (version) autofill('version', version[1]);
      if (form.dataset.autofill === 'mod') {
        autofill('title', stem.replace(/[_.]+/g, ' ').slice(0, 100));
        let name = file.name;
        if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,94}\.zip$/i.test(name) || /^(data_|bbmod_)/i.test(name)) {
          let safe = stem.replace(/[^A-Za-z0-9_.-]+/g, '_').replace(/^[_.-]+|[_.-]+$/g, '').slice(0, 90);
          if (!safe || /^(data_|bbmod_)/i.test(safe)) safe = 'mod_' + (crypto.randomUUID?.() || Date.now().toString(36)).replace(/-/g, '').slice(0, 12);
          name = safe + '.zip';
        }
        autofill('install_name', name);
      }
    };
    input.addEventListener('change', selected);
    ['dragenter', 'dragover'].forEach(type => zone.addEventListener(type, event => {
      event.preventDefault(); zone.classList.add('dragging');
    }));
    zone.addEventListener('dragleave', event => { if (!zone.contains(event.relatedTarget)) zone.classList.remove('dragging'); });
    zone.addEventListener('drop', event => {
      event.preventDefault(); zone.classList.remove('dragging');
      if (event.dataTransfer.files.length !== 1) {
        input.setCustomValidity('一次请选择一个文件。'); summary.textContent = '一次请选择一个文件。'; return;
      }
      input.files = event.dataTransfer.files;
      selected();
    });
    selected();
  });
  form.addEventListener('invalid', event => {
    const details = event.target.closest('details');
    if (details) details.open = true;
  }, true);
  form.addEventListener('submit', event => {
    if (!form.checkValidity()) return;
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button?.disabled) return;
    const status = form.querySelector('.upload-status');
    const progress = form.querySelector('.upload-progress');
    const oldLabel = button?.textContent;
    if (button) { button.disabled = true; button.textContent = '正在上传…'; }
    if (progress) { progress.hidden = false; progress.value = 0; }
    status.textContent = '正在上传文件…';
    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action || window.location.href);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.upload.onprogress = event => {
      if (!event.lengthComputable) return;
      const percent = Math.round(event.loaded * 100 / event.total);
      if (progress) progress.value = percent;
      status.textContent = percent < 100 ? `正在上传 ${percent}%` : '上传完成，正在检查文件并保存…';
    };
    const failed = message => {
      status.textContent = message;
      if (button) { button.disabled = false; button.textContent = oldLabel; }
      if (progress) progress.hidden = true;
    };
    xhr.onerror = () => failed('网络连接中断。文件仍已选中，可以重试；也可到版本列表确认是否已保存。');
    xhr.onload = () => {
      if (xhr.status === 200 && (xhr.getResponseHeader('Content-Type') || '').includes('application/json')) {
        try {
          const url = new URL(JSON.parse(xhr.responseText).redirect, window.location.origin);
          if (url.origin !== window.location.origin) throw new Error('Unexpected destination');
          window.location.assign(url.href); return;
        } catch { failed('无法确认上传结果，请到版本列表查看。'); return; }
      }
      if (xhr.status >= 500 || xhr.status === 413) {
        failed(xhr.status === 413 ? '文件超过服务器允许的上传大小。' : '服务器暂时无法保存，请稍后重试。'); return;
      }
      const next = new DOMParser().parseFromString(xhr.responseText, 'text/html').querySelector('#main');
      if (!next) { failed('无法读取上传结果，请刷新页面后重试。'); return; }
      // Keep the chosen file when validation asks the author to correct a field.
      form.querySelectorAll('input[type=file]').forEach(input => {
        const replacement = next.querySelector(`#${CSS.escape(input.id)}`);
        if (replacement) replacement.files = input.files;
      });
      document.querySelector('#main').replaceWith(next); bindPage(next);
      const error = next.querySelector('.field-errors, .notice.error');
      if (error) error.scrollIntoView({block: 'center', behavior: 'smooth'});
    };
    xhr.send(new FormData(form));
  });
});
}
bindPage();
