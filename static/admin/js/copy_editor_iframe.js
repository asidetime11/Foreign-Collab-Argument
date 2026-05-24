// Inline copy editor — runs inside the iframe loaded by the "界面文案" admin page.
// Edits never touch the parent DOM layout: textarea is positioned absolutely
// over the original element, original stays in place until commit.
(function() {
  if (window.top === window.self) return;

  var style = document.createElement('style');
  style.textContent =
    '.ui-copy { cursor: text !important; box-shadow: 0 0 0 2px #0a73b8 !important; outline: 2px dashed #0a73b8 !important; outline-offset: 2px !important; border-radius: 3px !important; background-color: rgba(10,115,184,.06) !important; transition: background-color .15s; min-width: 120px !important; min-height: 28px !important; display: inline-block !important; vertical-align: middle; position: relative !important; z-index: 9999 !important; pointer-events: auto !important; }' +
    '.ui-copy.ui-copy-multiline { display: block !important; min-height: 80px !important; }' +
    '.ui-copy:not(.editing):empty::before { content: "（点此编辑）"; color: #8aa5c2; font-style: italic; pointer-events: none; }' +
    '.ui-copy:hover { background-color: rgba(10,115,184,.15) !important; }' +
    '.ui-copy.editing { outline: 2px solid #0a73b8 !important; background-color: rgba(10,115,184,.04) !important; }' +
    '.ui-copy-input { box-sizing: border-box; padding: 4px 6px; border: 2px solid #0a73b8 !important; border-radius: 4px; font: inherit; color: inherit; background: #fff !important; word-break: break-word; overflow-wrap: anywhere; white-space: pre-wrap; outline: 0 !important; box-shadow: 0 4px 16px rgba(15,20,25,.12); z-index: 10000 !important; }' +
    '.ui-copy-input.multiline { resize: vertical; line-height: inherit; }' +
    '.finish-modal.finish-modal-flat { position: static !important; background: transparent !important; display: block !important; margin-top: 24px; }' +
    '.finish-modal.finish-modal-flat .finish-modal-panel { position: static !important; transform: none !important; max-width: 100% !important; box-shadow: 0 2px 8px rgba(0,0,0,.06) !important; }';
  document.head.appendChild(style);

  var dirty = {};
  var activeOverlay = null;

  function paragraphsToText(span) {
    return Array.prototype.map.call(span.querySelectorAll('p'), function(p) {
      return p.textContent;
    }).join('\n');
  }

  function textToParagraphs(span, text) {
    span.innerHTML = '';
    text.split('\n').forEach(function(line) {
      if (!line) return;
      var p = document.createElement('p');
      p.textContent = line;
      span.appendChild(p);
    });
  }

  function readCurrent(span) {
    var key = span.dataset.copyKey;
    if (dirty[key] !== undefined) return dirty[key];
    if ((span.dataset.copyRender || 'inline') === 'paragraphs') return paragraphsToText(span);
    return span.textContent;
  }

  function closeActive(reason) {
    if (!activeOverlay) return;
    var info = activeOverlay;
    activeOverlay = null;
    var span = info.span;
    var key = span.dataset.copyKey;
    var renderMode = span.dataset.copyRender || 'inline';
    var newVal = info.input.value;
    info.input.remove();
    span.classList.remove('editing');
    if (reason === 'cancel') return;
    // Commit
    if (renderMode === 'paragraphs') {
      textToParagraphs(span, newVal);
    } else {
      span.textContent = newVal;
    }
    if (newVal !== info.original) {
      dirty[key] = newVal;
      try { window.parent.postMessage({ type: 'copy:dirty', key: key, value: newVal }, '*'); } catch (e) {}
    }
  }

  function openEditor(span) {
    if (activeOverlay && activeOverlay.span === span) return;
    if (activeOverlay) closeActive('commit');

    var renderMode = span.dataset.copyRender || 'inline';
    var current = readCurrent(span);
    var multiline = renderMode === 'paragraphs'
      || span.classList.contains('ui-copy-multiline')
      || current.length > 40
      || /\n/.test(current);

    var rect = span.getBoundingClientRect();
    var cs = window.getComputedStyle(span);

    var input = document.createElement(multiline ? 'textarea' : 'input');
    if (!multiline) input.type = 'text';
    input.className = 'ui-copy-input' + (multiline ? ' multiline' : '');
    input.value = current;
    // Position: fixed (viewport-relative), covers the span exactly
    input.style.position = 'fixed';
    input.style.left = rect.left + 'px';
    input.style.top = rect.top + 'px';
    input.style.width = Math.max(rect.width, 140) + 'px';
    input.style.height = Math.max(rect.height, multiline ? 80 : 32) + 'px';
    input.style.font = cs.font;
    input.style.lineHeight = cs.lineHeight;
    input.style.color = cs.color;
    input.style.textAlign = cs.textAlign;

    // Block label/checkbox interactions from interfering
    ['mousedown', 'click', 'change', 'input', 'keydown', 'keyup'].forEach(function(ev) {
      input.addEventListener(ev, function(e) { e.stopPropagation(); });
    });

    span.classList.add('editing');
    document.body.appendChild(input);
    input.focus();
    if (!multiline) input.select();

    activeOverlay = { span: span, input: input, original: current };

    input.addEventListener('blur', function() {
      closeActive('commit');
    });
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeActive('cancel');
        e.preventDefault();
      } else if (e.key === 'Enter' && !multiline) {
        input.blur();
        e.preventDefault();
      }
    });
  }

  // Capture-phase: stop label/form taking the click before we react.
  document.addEventListener('mousedown', function(e) {
    if (activeOverlay && e.target === activeOverlay.input) return;
    var span = e.target.closest && e.target.closest('.ui-copy');
    if (!span) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
  }, true);
  document.addEventListener('click', function(e) {
    if (activeOverlay && e.target === activeOverlay.input) return;
    var span = e.target.closest && e.target.closest('.ui-copy');
    if (!span) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    openEditor(span);
  }, true);

  document.addEventListener('submit', function(e) { e.preventDefault(); }, true);
  document.querySelectorAll('a').forEach(function(a) {
    a.addEventListener('click', function(e) { e.preventDefault(); });
  });

  // Recalc overlay position on scroll/resize so it stays aligned
  function realign() {
    if (!activeOverlay) return;
    var rect = activeOverlay.span.getBoundingClientRect();
    activeOverlay.input.style.left = rect.left + 'px';
    activeOverlay.input.style.top = rect.top + 'px';
  }
  window.addEventListener('scroll', realign, true);
  window.addEventListener('resize', realign);

  window.addEventListener('message', function(e) {
    var msg = e.data;
    if (!msg || typeof msg !== 'object') return;
    if (msg.type === 'copy:get-values') {
      e.source.postMessage({ type: 'copy:values', values: dirty }, '*');
    } else if (msg.type === 'copy:reset') {
      dirty = {};
    }
  });

  try { window.parent.postMessage({ type: 'copy:ready' }, '*'); } catch (e) {}
})();
