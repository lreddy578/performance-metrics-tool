let allIssues = [];
let sortKey = '';
let sortAsc = true;

// ── API Calls ──────────────────────────────────────────────

async function loadMyIssues() {
  const max = document.getElementById('max-results').value;
  await fetchIssues(`/api/issues/my?max_results=${max}`, '👤 My Open Issues');
}

async function loadProjectIssues() {
  const key = document.getElementById('project-key').value.trim().toUpperCase();
  if (!key) { showStatus('Please enter a project key!', 'error'); return; }
  const max = document.getElementById('max-results').value;
  await fetchIssues(`/api/issues/project/${key}?max_results=${max}`, `📁 Project: ${key}`);
}

async function fetchIssues(url, title) {
  showLoader(true);
  hideAll();

  try {
    const response = await fetch(url);
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Unknown error');
    }

    allIssues = await response.json();
    renderTable(allIssues, title);
    showStatus(`✅ Loaded ${allIssues.length} issue(s) successfully.`, 'success');
  } catch (err) {
    showStatus(`❌ Error: ${err.message}`, 'error');
  } finally {
    showLoader(false);
  }
}

// ── Render ─────────────────────────────────────────────────

function renderTable(issues, title = 'Results') {
  document.getElementById('results-title').textContent = title;
  const tbody = document.getElementById('issues-body');
  tbody.innerHTML = '';

  if (issues.length === 0) {
    document.getElementById('empty-state').classList.remove('hidden');
    return;
  }

  issues.forEach(issue => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><a class="issue-key" href="${issue.url}" target="_blank">${issue.key}</a></td>
      <td>${escapeHtml(issue.summary)}</td>
      <td>${statusBadge(issue.status)}</td>
      <td class="${priorityClass(issue.priority)}">${issue.priority}</td>
      <td>${escapeHtml(issue.assignee)}</td>
      <td>${escapeHtml(issue.issue_type)}</td>
      <td>${issue.updated}</td>
    `;
    tbody.appendChild(tr);
  });

  updateStats(issues);
  document.getElementById('results-section').classList.remove('hidden');
  document.getElementById('stats').classList.remove('hidden');
}

// ── Stats ──────────────────────────────────────────────────

function updateStats(issues) {
  const inProgress = issues.filter(i => i.status.toLowerCase().includes('progress')).length;
  const highPriority = issues.filter(i =>
    ['highest', 'high'].includes(i.priority.toLowerCase())
  ).length;

  document.getElementById('stat-total').innerHTML =
    `<span>${issues.length}</span> Total Issues`;
  document.getElementById('stat-in-progress').innerHTML =
    `<span>${inProgress}</span> In Progress`;
  document.getElementById('stat-high-priority').innerHTML =
    `<span>${highPriority}</span> High Priority`;
}

// ── Filter ─────────────────────────────────────────────────

function filterTable() {
  const query = document.getElementById('filter-input').value.toLowerCase();
  const filtered = allIssues.filter(issue =>
    Object.values(issue).some(val =>
      String(val).toLowerCase().includes(query)
    )
  );
  renderTable(filtered, document.getElementById('results-title').textContent);
}

// ── Sort ───────────────────────────────────────────────────

function sortTable(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  else { sortKey = key; sortAsc = true; }

  const sorted = [...allIssues].sort((a, b) => {
    const valA = String(a[key] || '').toLowerCase();
    const valB = String(b[key] || '').toLowerCase();
    return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
  });

  renderTable(sorted, document.getElementById('results-title').textContent);
}

// ── Helpers ────────────────────────────────────────────────

function statusBadge(status) {
  const s = status.toLowerCase();
  let cls = 'badge-todo';
  if (s.includes('progress')) cls = 'badge-inprogress';
  else if (s.includes('done') || s.includes('closed')) cls = 'badge-done';
  else if (s.includes('block')) cls = 'badge-blocked';
  return `<span class="badge ${cls}">${status}</span>`;
}

function priorityClass(priority) {
  const p = priority.toLowerCase();
  if (p === 'highest' || p === 'high') return 'priority-high';
  if (p === 'medium') return 'priority-medium';
  return 'priority-low';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

function showStatus(message, type) {
  const bar = document.getElementById('status-bar');
  bar.textContent = message;
  bar.className = `status-bar ${type}`;
  bar.classList.remove('hidden');
  setTimeout(() => bar.classList.add('hidden'), 5000);
}

function showLoader(show) {
  document.getElementById('loader').classList.toggle('hidden', !show);
}

function hideAll() {
  ['results-section', 'stats', 'empty-state'].forEach(id =>
    document.getElementById(id).classList.add('hidden')
  );
}