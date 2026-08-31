/**
 * Minimal hash router. Each top-level "page" the brief asked for
 * (home / dashboard / dna / journey) is its own <section data-view="...">
 * element — switching routes toggles visibility rather than dumping
 * everything into one long scroll. Auth and onboarding remain overlays
 * on top, since they gate access rather than being a destination.
 */
const Router = (function () {
  const views = {};
  let current = null;
  const guards = []; // fn(route) -> redirect route string | null

  function register(name, el) {
    views[name] = el;
  }

  function addGuard(fn) {
    guards.push(fn);
  }

  function parse() {
    const hash = location.hash.replace(/^#\/?/, '');
    return hash || 'home';
  }

  function go(route) {
    if (location.hash.replace(/^#\/?/, '') === route) {
      render(route);
    } else {
      location.hash = '#/' + route;
    }
  }

  function render(route) {
    for (const fn of guards) {
      const redirect = fn(route);
      if (redirect && redirect !== route) {
        location.hash = '#/' + redirect;
        return;
      }
    }
    if (!views[route]) route = 'home';
    current = route;
    Object.entries(views).forEach(([name, el]) => {
      el.classList.toggle('view-active', name === route);
    });
    document.querySelectorAll('.page-nav a[data-route]').forEach((a) => {
      a.classList.toggle('active', a.dataset.route === route);
      a.setAttribute('aria-current', a.dataset.route === route ? 'page' : 'false');
    });
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
    window.dispatchEvent(new CustomEvent('routechange', { detail: { route } }));
  }

  window.addEventListener('hashchange', () => render(parse()));

  function start() {
    render(parse());
  }

  function getCurrent() { return current; }

  return { register, addGuard, go, start, getCurrent };
})();
