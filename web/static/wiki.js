(() => {
  'use strict';
  const root = document.querySelector('.wiki-shell');
  if (!root) return;
  if (root.dataset.wikiMode === 'en') {
    root.querySelectorAll('a[href^="/wiki/read/"]').forEach(link => {
      const url = new URL(link.getAttribute('href'), location.origin);
      url.searchParams.set('lang', 'en');
      link.href = url.pathname + url.search + url.hash;
    });
  }
  if (matchMedia('(max-width: 800px)').matches) {
    root.querySelectorAll('.wiki-contents details').forEach(details => { details.open = false; });
  }
  // Sorting is offered only for independent rows; merged-cell tables keep their order.
  root.querySelectorAll('.wiki-content table.w-sortable').forEach(table => {
    if (table.querySelector('[rowspan], [colspan], table')) return;
    const rows = Array.from(table.rows);
    const header = rows[0];
    if (!header || !header.querySelector('th') || rows.length < 3) return;
    const body = rows[1].parentElement;
    if (!rows.slice(1).every(row => row.parentElement === body)) return;
    Array.from(header.cells).forEach((cell, index) => {
      if (cell.classList.contains('w-unsortable')) return;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'wiki-sort-button';
      button.append(...Array.from(cell.childNodes));
      button.setAttribute('aria-label', `按 ${button.textContent.trim() || cell.querySelector('img')?.alt || '此列'} 排序`);
      cell.append(button);
      button.addEventListener('click', () => {
        const ascending = cell.getAttribute('aria-sort') !== 'ascending';
        Array.from(header.cells).forEach(th => th.removeAttribute('aria-sort'));
        cell.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        button.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        const value = row => {
          const td = row.cells[index];
          return (td?.dataset.sortValue || td?.textContent || '').trim();
        };
        rows.slice(1).sort((a, b) => {
          const av = value(a), bv = value(b);
          const an = Number(av.replace(/[%+,]/g, '').replace(/−/g, '-'));
          const bn = Number(bv.replace(/[%+,]/g, '').replace(/−/g, '-'));
          const diff = av && bv && Number.isFinite(an) && Number.isFinite(bn)
            ? an - bn : av.localeCompare(bv, undefined, { numeric: true });
          return ascending ? diff : -diff;
        }).forEach(row => body.append(row));
      });
    });
  });
  root.querySelectorAll('.wiki-content .w-mw-collapsible').forEach(container => {
    if (container.matches('table') || container.closest('table')) return;
    const contents = container.querySelector('.w-mw-collapsible-content');
    if (!contents) return;
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'wiki-collapse-button';
    button.textContent = '展开详情'; button.setAttribute('aria-expanded', 'false');
    contents.hidden = true; contents.before(button);
    button.addEventListener('click', () => {
      contents.hidden = !contents.hidden;
      button.textContent = contents.hidden ? '展开详情' : '收起详情';
      button.setAttribute('aria-expanded', String(!contents.hidden));
    });
  });
  const revealAnchor = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    if (!id) return;
    const target = document.getElementById(id);
    if (!target) return;
    let parent = target.parentElement;
    while (parent && parent !== root) {
      if (parent instanceof HTMLDetailsElement) parent.open = true;
      if (parent.hidden) {
        parent.hidden = false;
        const toggle = parent.previousElementSibling;
        if (toggle?.classList.contains('wiki-collapse-button')) {
          toggle.textContent = '收起详情'; toggle.setAttribute('aria-expanded', 'true');
        }
      }
      parent = parent.parentElement;
    }
  };
  window.addEventListener('hashchange', revealAnchor);
  revealAnchor();
})();
