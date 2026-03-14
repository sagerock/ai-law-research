// ── Mindmapper Module ────────────────────────────────────────
// ES module refactored from standalone mindmapper.js
// Usage: initMindmapper(containerDiv, { onSave(tree), onDirty() })
//   returns { loadMap(json), getTree(), destroy() }

const NODE_W = 180, NODE_MIN_H = 40, H_GAP = 60, V_GAP = 12;
const TEXT_PAD_X = 12, TEXT_PAD_Y = 10, LINE_H = 18, MAX_CHARS = 22;
const DEPTH_COLORS = ['#6b7f6b', '#8fa88f', '#a3b899', '#c2ccb2']; // sage palette
const COLLAPSE_R = 10;

function wrapText(text) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = '';
  for (const word of words) {
    const test = line ? line + ' ' + word : word;
    if (test.length > MAX_CHARS && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines.length ? lines : [''];
}

function nodeHeight(node) {
  const lines = wrapText(node.text);
  node._lines = lines;
  return Math.max(NODE_MIN_H, TEXT_PAD_Y * 2 + lines.length * LINE_H);
}

function genId(state) { return 'node_' + (state.nextId++); }

function findNode(node, id) {
  if (!node) return null;
  if (node.id === id) return node;
  for (const c of node.children) {
    const r = findNode(c, id);
    if (r) return r;
  }
  return null;
}

function findParent(node, id) {
  if (!node) return null;
  for (const c of node.children) {
    if (c.id === id) return node;
    const r = findParent(c, id);
    if (r) return r;
  }
  return null;
}

function createNode(state, text) {
  return { id: genId(state), text, collapsed: false, children: [] };
}

function maxIdIn(node) {
  let m = parseInt(node.id.split('_')[1]) || 0;
  for (const c of node.children) m = Math.max(m, maxIdIn(c));
  return m;
}

function isDescendant(ancestor, id) {
  for (const c of ancestor.children) {
    if (c.id === id || isDescendant(c, id)) return true;
  }
  return false;
}

function depthColor(d) { return DEPTH_COLORS[Math.min(d, DEPTH_COLORS.length - 1)]; }

// ── Layout ─────────────────────────────────────────────────
function layoutTree(node, depth, yOffset) {
  const visibleChildren = node.collapsed ? [] : node.children;
  node._x = depth * (NODE_W + H_GAP);
  node._depth = depth;
  node._h = nodeHeight(node);

  if (visibleChildren.length === 0) {
    node._y = yOffset;
    node._subtreeH = node._h;
    return yOffset + node._h + V_GAP;
  }

  let y = yOffset;
  for (const child of visibleChildren) {
    y = layoutTree(child, depth + 1, y);
  }

  const first = visibleChildren[0];
  const last = visibleChildren[visibleChildren.length - 1];
  const firstMid = first._y + first._h / 2;
  const lastMid = last._y + last._h / 2;
  node._y = (firstMid + lastMid) / 2 - node._h / 2;
  node._subtreeH = y - yOffset - V_GAP;
  return y;
}

function stripLayout(node) {
  const { _x, _y, _h, _depth, _subtreeH, _lines, ...clean } = node;
  return { ...clean, children: node.children.map(stripLayout) };
}

// ── Main init ──────────────────────────────────────────────
export function initMindmapper(container, callbacks = {}) {
  const { onSave, onDirty } = callbacks;

  const state = {
    root: null,
    selectedId: null,
    nextId: 100,
    pan: { x: 60, y: 0 },
    zoom: 1,
    dragging: false,
    dragStart: { x: 0, y: 0 },
    panStart: { x: 0, y: 0 },
    nodeDrag: null,
    dirty: false,
  };

  // Create DOM inside container
  container.style.position = 'relative';
  container.style.overflow = 'hidden';
  container.style.background = '#faf8f5'; // cream

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');
  svg.style.display = 'block';
  svg.style.cursor = 'grab';
  container.appendChild(svg);

  const viewport = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  viewport.setAttribute('id', 'mm-viewport');
  svg.appendChild(viewport);

  // Rename input
  const renameInput = document.createElement('textarea');
  renameInput.style.cssText = 'position:absolute;display:none;z-index:100;font:14px/1.3 system-ui,sans-serif;padding:8px 12px;border:2px solid #6b7f6b;border-radius:8px;background:#fff;resize:none;outline:none;box-sizing:border-box;';
  container.appendChild(renameInput);

  // Toolbar
  const toolbar = document.createElement('div');
  toolbar.style.cssText = 'position:absolute;top:8px;right:8px;z-index:50;display:flex;gap:4px;background:white;border:1px solid #d6d3d1;border-radius:10px;padding:4px 6px;box-shadow:0 2px 8px rgba(0,0,0,0.08);';
  const toolbarButtons = [
    { label: '+', title: 'Add child (Tab)', action: () => addChild() },
    { label: '↵', title: 'Add sibling (Enter)', action: () => addSibling() },
    { label: '✕', title: 'Delete (Del)', action: () => deleteSelected() },
    { label: '↑', title: 'Move up (Alt+↑)', action: () => moveNode(-1) },
    { label: '↓', title: 'Move down (Alt+↓)', action: () => moveNode(1) },
    { label: '⊟', title: 'Collapse all', action: () => collapseAll() },
    { label: '⊞', title: 'Expand all + fit', action: () => expandAll() },
    { label: '⌖', title: 'Center / fit view', action: () => fitView() },
    { label: '−', title: 'Zoom out', action: () => applyZoom(1 / 1.2) },
    { label: null, title: null, action: null, isLabel: true }, // zoom label
    { label: '+', title: 'Zoom in', action: () => applyZoom(1.2) },
  ];

  let zoomLabel;
  for (const btn of toolbarButtons) {
    if (btn.isLabel) {
      zoomLabel = document.createElement('span');
      zoomLabel.style.cssText = 'font-size:11px;color:#78716c;min-width:36px;text-align:center;line-height:28px;';
      zoomLabel.textContent = '100%';
      toolbar.appendChild(zoomLabel);
      continue;
    }
    const b = document.createElement('button');
    b.textContent = btn.label;
    b.title = btn.title;
    b.style.cssText = 'width:28px;height:28px;border:none;background:transparent;cursor:pointer;border-radius:6px;font-size:14px;color:#57534e;display:flex;align-items:center;justify-content:center;';
    b.addEventListener('mouseenter', () => { b.style.background = '#f5f5f4'; });
    b.addEventListener('mouseleave', () => { b.style.background = 'transparent'; });
    b.addEventListener('click', btn.action);
    toolbar.appendChild(b);
  }
  container.appendChild(toolbar);

  // SVG styles
  const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  styleEl.textContent = `
    .node-rect { rx: 10; ry: 10; cursor: pointer; stroke: transparent; stroke-width: 2; transition: filter 0.15s; }
    .node-rect:hover { filter: brightness(1.08); }
    .node-rect.selected { stroke: #d4a843; stroke-width: 3; filter: drop-shadow(0 0 6px rgba(212,168,67,0.4)); }
    .node-rect.drop-target { stroke: #ef4444; stroke-width: 3; stroke-dasharray: 6 3; }
    .node-text { fill: white; font: 13px/1.3 system-ui, sans-serif; pointer-events: none; }
    .edge { fill: none; stroke: #d6d3d1; stroke-width: 2; }
    .collapse-circle { fill: #f5f5f4; stroke: #d6d3d1; stroke-width: 1.5; cursor: pointer; }
    .collapse-text { fill: #78716c; font: bold 14px monospace; pointer-events: none; }
  `;
  svg.appendChild(styleEl);

  // ── Render ────────────────────────────────────────────────
  function render() {
    if (!state.root) return;
    layoutTree(state.root, 0, 0);

    const rect = container.getBoundingClientRect();
    if (state.pan.y === 0) {
      state.pan.y = rect.height / 2 - state.root._y;
    }

    viewport.setAttribute('transform',
      `translate(${state.pan.x},${state.pan.y}) scale(${state.zoom})`);

    viewport.innerHTML = '';
    // Re-add style
    viewport.parentNode.insertBefore(styleEl, viewport);
    renderEdges(state.root);
    renderNodes(state.root);
  }

  function renderEdges(node) {
    if (node.collapsed) return;
    for (const child of node.children) {
      const x1 = node._x + NODE_W;
      const y1 = node._y + node._h / 2;
      const x2 = child._x;
      const y2 = child._y + child._h / 2;
      const cx = (x1 + x2) / 2;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`);
      path.setAttribute('class', 'edge');
      viewport.appendChild(path);

      renderEdges(child);
    }
  }

  function renderNodes(node) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', node._x);
    rect.setAttribute('y', node._y);
    rect.setAttribute('width', NODE_W);
    rect.setAttribute('height', node._h);
    rect.setAttribute('fill', depthColor(node._depth));
    rect.setAttribute('class', 'node-rect' + (node.id === state.selectedId ? ' selected' : ''));
    rect.dataset.id = node.id;
    g.appendChild(rect);

    const lines = node._lines || wrapText(node.text);
    const textBlockH = lines.length * LINE_H;
    const textStartY = node._y + (node._h - textBlockH) / 2 + LINE_H * 0.75;
    const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    txt.setAttribute('class', 'node-text');
    for (let i = 0; i < lines.length; i++) {
      const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
      tspan.setAttribute('x', node._x + TEXT_PAD_X);
      tspan.setAttribute('y', textStartY + i * LINE_H);
      tspan.textContent = lines[i];
      txt.appendChild(tspan);
    }
    g.appendChild(txt);

    if (node.children.length > 0) {
      const cx = node._x + NODE_W + COLLAPSE_R + 4;
      const cy = node._y + node._h / 2;

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', cx);
      circle.setAttribute('cy', cy);
      circle.setAttribute('r', COLLAPSE_R);
      circle.setAttribute('class', 'collapse-circle');
      circle.dataset.collapseId = node.id;
      g.appendChild(circle);

      const sym = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sym.setAttribute('x', cx);
      sym.setAttribute('y', cy + 4);
      sym.setAttribute('text-anchor', 'middle');
      sym.setAttribute('class', 'collapse-text');
      sym.textContent = node.collapsed ? '+' : '−';
      sym.dataset.collapseId = node.id;
      g.appendChild(sym);
    }

    viewport.appendChild(g);
    if (!node.collapsed) {
      for (const child of node.children) renderNodes(child);
    }
  }

  // ── Node Operations ──────────────────────────────────────
  function markDirty() {
    state.dirty = true;
    if (onDirty) onDirty();
  }

  function addChild() {
    const parent = findNode(state.root, state.selectedId);
    if (!parent) return;
    parent.collapsed = false;
    const child = createNode(state, 'New Node');
    parent.children.push(child);
    state.selectedId = child.id;
    markDirty();
    render();
    startRename(child.id);
  }

  function addSibling() {
    if (!state.selectedId || state.selectedId === state.root.id) return;
    const parent = findParent(state.root, state.selectedId);
    if (!parent) return;
    const idx = parent.children.findIndex(c => c.id === state.selectedId);
    const sib = createNode(state, 'New Node');
    parent.children.splice(idx + 1, 0, sib);
    state.selectedId = sib.id;
    markDirty();
    render();
    startRename(sib.id);
  }

  function moveNode(dir) {
    if (!state.selectedId || state.selectedId === state.root.id) return;
    const parent = findParent(state.root, state.selectedId);
    if (!parent) return;
    const idx = parent.children.findIndex(c => c.id === state.selectedId);
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= parent.children.length) return;
    [parent.children[idx], parent.children[newIdx]] = [parent.children[newIdx], parent.children[idx]];
    markDirty();
    render();
  }

  function deleteSelected() {
    if (!state.selectedId || state.selectedId === state.root.id) return;
    const parent = findParent(state.root, state.selectedId);
    if (!parent) return;
    parent.children = parent.children.filter(c => c.id !== state.selectedId);
    state.selectedId = parent.id;
    markDirty();
    render();
  }

  // ── Inline Rename ────────────────────────────────────────
  function startRename(nodeId) {
    const node = findNode(state.root, nodeId);
    if (!node) return;

    const rects = viewport.querySelectorAll('.node-rect');
    let targetRect = null;
    for (const r of rects) {
      if (r.dataset.id === nodeId) { targetRect = r; break; }
    }
    if (!targetRect) return;

    const box = targetRect.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    renameInput.style.left = (box.left - containerRect.left) + 'px';
    renameInput.style.top = (box.top - containerRect.top) + 'px';
    renameInput.style.width = box.width + 'px';
    renameInput.style.height = Math.max(box.height, 40) + 'px';
    renameInput.style.display = 'block';
    renameInput.value = node.text;
    renameInput.dataset.id = nodeId;
    renameInput.select();
    renameInput.focus();
  }

  function commitRename() {
    if (renameInput.style.display === 'none') return;
    const node = findNode(state.root, renameInput.dataset.id);
    if (node && renameInput.value.trim()) {
      node.text = renameInput.value.trim();
      markDirty();
    }
    renameInput.style.display = 'none';
    render();
  }

  renameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); commitRename(); }
    if (e.key === 'Escape') { renameInput.style.display = 'none'; }
    e.stopPropagation();
  });
  renameInput.addEventListener('blur', commitRename);

  // ── SVG Events ────────────────────────────────────────────
  const DRAG_THRESHOLD = 8;

  function hitTestNode(clientX, clientY) {
    const rects = viewport.querySelectorAll('.node-rect');
    for (const r of rects) {
      const box = r.getBoundingClientRect();
      if (clientX >= box.left && clientX <= box.right &&
          clientY >= box.top && clientY <= box.bottom) {
        return r.dataset.id;
      }
    }
    return null;
  }

  function createGhost(node) {
    const el = document.createElement('div');
    el.style.cssText = `position:fixed;padding:6px 14px;border-radius:8px;color:white;font:13px system-ui;pointer-events:none;z-index:200;opacity:0.9;background:${depthColor(node._depth)};`;
    el.textContent = node.text;
    document.body.appendChild(el);
    return el;
  }

  function cleanupNodeDrag() {
    if (state.nodeDrag) {
      if (state.nodeDrag.ghost) state.nodeDrag.ghost.remove();
      const prev = viewport.querySelector('.node-rect.drop-target');
      if (prev) prev.classList.remove('drop-target');
      state.nodeDrag = null;
    }
  }

  function onPointerDown(e) {
    if (e.target.dataset && e.target.dataset.collapseId) {
      const node = findNode(state.root, e.target.dataset.collapseId);
      if (node) { node.collapsed = !node.collapsed; render(); }
      return;
    }

    if (e.target.dataset && e.target.dataset.id) {
      state.nodeDrag = {
        id: e.target.dataset.id,
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        active: false,
        ghost: null,
        dropTargetId: null,
      };
      return;
    }

    state.dragging = true;
    state.dragStart = { x: e.clientX, y: e.clientY };
    state.panStart = { ...state.pan };
    svg.style.cursor = 'grabbing';
    svg.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e) {
    if (state.nodeDrag) {
      const dx = e.clientX - state.nodeDrag.startX;
      const dy = e.clientY - state.nodeDrag.startY;

      if (!state.nodeDrag.active) {
        if (Math.abs(dx) + Math.abs(dy) < DRAG_THRESHOLD) return;
        const dragNode = findNode(state.root, state.nodeDrag.id);
        if (!dragNode || state.nodeDrag.id === state.root.id) {
          state.nodeDrag = null;
          return;
        }
        state.nodeDrag.active = true;
        state.nodeDrag.ghost = createGhost(dragNode);
        try { svg.setPointerCapture(state.nodeDrag.pointerId); } catch {}
      }

      state.nodeDrag.ghost.style.left = (e.clientX + 12) + 'px';
      state.nodeDrag.ghost.style.top = (e.clientY - 16) + 'px';

      state.nodeDrag.ghost.style.display = 'none';
      const targetId = hitTestNode(e.clientX, e.clientY);
      state.nodeDrag.ghost.style.display = '';

      const prevTarget = viewport.querySelector('.node-rect.drop-target');
      if (prevTarget) prevTarget.classList.remove('drop-target');

      const draggedNode = findNode(state.root, state.nodeDrag.id);
      if (targetId && targetId !== state.nodeDrag.id && !isDescendant(draggedNode, targetId)) {
        state.nodeDrag.dropTargetId = targetId;
        const rects = viewport.querySelectorAll('.node-rect');
        for (const r of rects) {
          if (r.dataset.id === targetId) { r.classList.add('drop-target'); break; }
        }
      } else {
        state.nodeDrag.dropTargetId = null;
      }
      return;
    }

    if (!state.dragging) return;
    state.pan.x = state.panStart.x + (e.clientX - state.dragStart.x);
    state.pan.y = state.panStart.y + (e.clientY - state.dragStart.y);
    viewport.setAttribute('transform',
      `translate(${state.pan.x},${state.pan.y}) scale(${state.zoom})`);
  }

  function onPointerUp(e) {
    if (state.nodeDrag) {
      if (state.nodeDrag.active && state.nodeDrag.dropTargetId) {
        const dragId = state.nodeDrag.id;
        const dropId = state.nodeDrag.dropTargetId;
        const dragNode = findNode(state.root, dragId);
        const oldParent = findParent(state.root, dragId);
        const newParent = findNode(state.root, dropId);

        if (dragNode && oldParent && newParent) {
          oldParent.children = oldParent.children.filter(c => c.id !== dragId);
          newParent.collapsed = false;
          newParent.children.push(dragNode);
          state.selectedId = dragId;
          markDirty();
          cleanupNodeDrag();
          render();
          return;
        }
      }

      const wasActive = state.nodeDrag.active;
      const nodeId = state.nodeDrag.id;
      cleanupNodeDrag();

      if (!wasActive) {
        state.selectedId = nodeId;
        render();
      }
      return;
    }

    state.dragging = false;
    svg.style.cursor = 'grab';
  }

  function onDblClick(e) {
    if (e.target.dataset && e.target.dataset.id) {
      state.selectedId = e.target.dataset.id;
      startRename(e.target.dataset.id);
    }
  }

  function onWheel(e) {
    if (!e.ctrlKey) return;
    e.preventDefault();
    const clamped = Math.max(-3, Math.min(3, e.deltaY));
    const factor = 1 - clamped * 0.03;
    applyZoom(factor);
  }

  svg.addEventListener('pointerdown', onPointerDown);
  svg.addEventListener('pointermove', onPointerMove);
  svg.addEventListener('pointerup', onPointerUp);
  svg.addEventListener('dblclick', onDblClick);
  svg.addEventListener('wheel', onWheel, { passive: false });

  // ── Keyboard ──────────────────────────────────────────────
  function onKeyDown(e) {
    if (renameInput.style.display !== 'none') return;

    if (e.altKey && e.key === 'ArrowUp') { e.preventDefault(); moveNode(-1); return; }
    if (e.altKey && e.key === 'ArrowDown') { e.preventDefault(); moveNode(1); return; }

    if (e.key === 'Tab') { e.preventDefault(); addChild(); }
    else if (e.key === 'Enter') { e.preventDefault(); addSibling(); }
    else if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); deleteSelected(); }
    else if (e.key === 'Escape') { state.selectedId = null; render(); }
    else if (e.key === 'F2') { if (state.selectedId) startRename(state.selectedId); }
    else { return; } // don't stop propagation for unhandled keys
    e.stopPropagation();
  }

  container.setAttribute('tabindex', '0');
  container.addEventListener('keydown', onKeyDown);

  // ── Zoom ──────────────────────────────────────────────────
  function applyZoom(factor) {
    state.zoom = Math.max(0.3, Math.min(3, state.zoom * factor));
    if (zoomLabel) zoomLabel.textContent = Math.round(state.zoom * 100) + '%';
    render();
  }

  // ── Collapse / Expand All ──────────────────────────────────
  function setCollapsedAll(node, collapsed) {
    if (node.children.length > 0) node.collapsed = collapsed;
    for (const c of node.children) setCollapsedAll(c, collapsed);
  }

  function collapseAll() {
    if (!state.root) return;
    setCollapsedAll(state.root, true);
    state.root.collapsed = false; // keep root open
    render();
    fitView();
  }

  function expandAll() {
    if (!state.root) return;
    setCollapsedAll(state.root, false);
    render();
    fitView();
  }

  // ── Fit View ──────────────────────────────────────────────
  function fitView() {
    if (!state.root) return;
    layoutTree(state.root, 0, 0);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    function walk(n) {
      minX = Math.min(minX, n._x);
      minY = Math.min(minY, n._y);
      maxX = Math.max(maxX, n._x + NODE_W);
      maxY = Math.max(maxY, n._y + n._h);
      if (!n.collapsed) n.children.forEach(walk);
    }
    walk(state.root);

    const treeW = maxX - minX + 40;
    const treeH = maxY - minY + 40;
    const rect = container.getBoundingClientRect();
    const viewW = rect.width;
    const viewH = rect.height;
    state.zoom = Math.min(1.5, Math.min(viewW / treeW, viewH / treeH));
    state.pan.x = (viewW - treeW * state.zoom) / 2 - minX * state.zoom;
    state.pan.y = (viewH - treeH * state.zoom) / 2 - minY * state.zoom;
    if (zoomLabel) zoomLabel.textContent = Math.round(state.zoom * 100) + '%';
    render();
  }

  // ── Public API ────────────────────────────────────────────
  function loadMap(data) {
    // data can be JSON string or parsed object
    const parsed = typeof data === 'string' ? JSON.parse(data) : data;
    const root = parsed.root || parsed;
    if (!root.id || !root.text) throw new Error('Invalid mindmap: missing root.id or root.text');
    state.root = root;
    state.selectedId = root.id;
    state.nextId = maxIdIn(root) + 1;
    state.pan = { x: 60, y: 0 };
    state.zoom = 1;
    state.dirty = false;
    render();
    // Fit after a tick so container dimensions are settled
    setTimeout(fitView, 50);
  }

  function getTree() {
    if (!state.root) return null;
    return { version: 1, name: state.root.text, root: stripLayout(state.root) };
  }

  function destroy() {
    svg.removeEventListener('pointerdown', onPointerDown);
    svg.removeEventListener('pointermove', onPointerMove);
    svg.removeEventListener('pointerup', onPointerUp);
    svg.removeEventListener('dblclick', onDblClick);
    svg.removeEventListener('wheel', onWheel);
    container.removeEventListener('keydown', onKeyDown);
    container.innerHTML = '';
  }

  // Load blank map by default
  const blankRoot = { id: 'node_1', text: 'New Mind Map', collapsed: false, children: [] };
  loadMap({ root: blankRoot });

  return { loadMap, getTree, destroy };
}
