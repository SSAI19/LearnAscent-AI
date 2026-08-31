/**
 * Daily + Weekly Tasks module (Learning Journey page).
 *
 * Data-honesty contract:
 *  - Every task rendered here is a real roadmap topic returned by
 *    GET /api/engines/tasks, which itself re-runs the existing roadmap
 *    engine live for the learner's current career + skill state.
 *  - Checking a task calls POST /api/engines/tasks/complete, which
 *    persists a TaskCompletion row server-side and returns the refreshed
 *    list. The checkbox never just toggles a local/visual flag — if the
 *    request fails, the box reverts.
 *  - onProgressChange(payload) is called after every successful
 *    complete/uncomplete so app.js can re-fetch profile/readiness and
 *    re-render the Mountain + Learner DNA from the same real numbers.
 */
const Tasks = (function () {
  let els = {};
  let onProgressChange = null;

  function init(ids) {
    els = {
      container: document.getElementById(ids.container),
      todayList: document.getElementById(ids.todayList),
      todayCount: document.getElementById(ids.todayCount),
      todayEmpty: document.getElementById(ids.todayEmpty),
      weekList: document.getElementById(ids.weekList),
      weekCount: document.getElementById(ids.weekCount),
    };
  }

  function setProgressListener(fn) {
    onProgressChange = fn;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function checkIconSvg() {
    return '<svg viewBox="0 0 16 16" fill="none"><path d="M3 8.5 L6.5 12 L13 4" stroke="#08070a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  function taskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card' + (task.completed ? ' done' : '');
    card.dataset.topicId = task.id;

    const check = document.createElement('button');
    check.type = 'button';
    check.className = 'task-check' + (task.completed ? ' checked' : '');
    check.setAttribute('aria-pressed', String(!!task.completed));
    check.innerHTML = checkIconSvg();

    const body = document.createElement('div');
    body.className = 'task-body';
    const trackLabel = task.track === 'technical'
      ? I18N.t('journey.legend_technical') : I18N.t('journey.legend_professional');
    body.innerHTML = `
      <div class="task-title">${escapeHtml(task.label)}</div>
      <div class="task-meta">
        <span class="track-${task.track}">${trackLabel}</span>
        <span>${task.estimated_hours}h</span>
        <span>${I18N.t('tasks.week_label')} ${task.week_number}</span>
      </div>
      ${task.detail ? `<div class="task-detail">${escapeHtml(task.detail)}</div>` : ''}
    `;

    check.addEventListener('click', () => toggleTask(task, check, card));

    card.appendChild(check);
    card.appendChild(body);
    return card;
  }

  async function toggleTask(task, checkEl, cardEl) {
    checkEl.disabled = true;
    const wasCompleted = task.completed;
    try {
      const result = wasCompleted
        ? await learner.uncompleteTask(task.id)
        : await learner.completeTask(task.id);
      render(result);
      if (onProgressChange) onProgressChange(result);
    } catch (e) {
      console.error('tasks: toggle failed', e);
      checkEl.disabled = false;
    }
  }

  /**
   * data: TasksResponse { today, this_week, week_number, completed_count, total_count }
   */
  function render(data) {
    if (!els.container) return;
    data = data || { today: [], this_week: [], completed_count: 0, total_count: 0 };

    if (!data.total_count) {
      els.container.style.display = 'none';
      return;
    }
    els.container.style.display = 'block';

    els.todayList.innerHTML = '';
    if (!data.today.length) {
      els.todayEmpty.style.display = 'block';
    } else {
      els.todayEmpty.style.display = 'none';
      data.today.forEach((t) => els.todayList.appendChild(taskCard(t)));
    }
    const todayDone = data.today.filter((t) => t.completed).length;
    els.todayCount.textContent = `${todayDone}/${data.today.length}`;

    els.weekList.innerHTML = '';
    data.this_week.forEach((t) => els.weekList.appendChild(taskCard(t)));
    const weekDone = data.this_week.filter((t) => t.completed).length;
    els.weekCount.textContent = `${weekDone}/${data.this_week.length}`;
  }

  /**
   * Fetch the real task list from the backend and render it. Call this
   * whenever the Journey page is entered (or after boot, if already on
   * it) so it never shows stale state.
   */
  async function load() {
    try {
      const data = await learner.getTasks();
      render(data);
      return data;
    } catch (e) {
      console.error('tasks: load failed', e);
      if (els.container) els.container.style.display = 'none';
      return null;
    }
  }

  return { init, load, render, setProgressListener };
})();
