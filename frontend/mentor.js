/* AI Mentor — flying companion.
 * Idle: hovers/bobs gently in its home corner.
 * Click: flies from the corner to a docked position beside the chat
 *   panel using an actual animated transform path (translate + slight
 *   arc + rotation), not display:none/block.
 * Close: flies back to its home position with the same treatment.
 */
const Mentor = (function () {
  let robot, panel, home = { x: 0, y: 0 };
  let flying = false;
  let open = false;
  let readyCheck = () => false;

  function init(robotId, panelId) {
    robot = document.getElementById(robotId);
    panel = document.getElementById(panelId);
    if (!robot || !panel) return;

    robot.addEventListener('click', toggle);
    window.addEventListener('resize', () => { if (!open) snapHome(); });
    snapHome();
  }

  function setReadyCheck(fn) {
    readyCheck = fn;
  }

  function snapHome() {
    robot.style.transform = 'translate(0px, 0px) rotate(0deg)';
  }

  function toggle() {
    if (flying) return;
    open ? close() : flyOpen();
  }

  function flyOpen() {
    flying = true;
    robot.classList.add('flying');
    robot.classList.remove('idle-float');

    const robotRect = robot.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    // Target: hover just above/left of the panel's anchor point, where
    // the panel will visually "dock" once open.
    const targetX = (panelRect.left + panelRect.width / 2) - (robotRect.left + robotRect.width / 2);
    const targetY = (panelRect.top - 10) - (robotRect.top + robotRect.height / 2);

    robot.style.transition = 'transform 0.85s cubic-bezier(0.22, 1, 0.36, 1)';
    // A gentle arc: overshoot slightly upward mid-flight via a two-step
    // transform using a short timeout keyframe, then settle.
    requestAnimationFrame(() => {
      robot.style.transform = `translate(${targetX * 0.55}px, ${targetY - 40}px) rotate(-8deg) scale(1.05)`;
      setTimeout(() => {
        robot.style.transform = `translate(${targetX}px, ${targetY}px) rotate(0deg) scale(1)`;
      }, 260);
    });

    setTimeout(() => {
      panel.classList.add('open');
      flying = false;
      open = true;
      if (window.MentorChat) MentorChat.onOpen(!!readyCheck());
    }, 850);
  }

  function close() {
    flying = true;
    panel.classList.remove('open');
    robot.style.transition = 'transform 0.75s cubic-bezier(0.4, 0, 0.2, 1)';
    requestAnimationFrame(() => {
      robot.style.transform = 'translate(30px, -30px) rotate(6deg) scale(1.03)';
      setTimeout(() => {
        robot.style.transform = 'translate(0px, 0px) rotate(0deg) scale(1)';
      }, 260);
    });
    setTimeout(() => {
      robot.classList.remove('flying');
      robot.classList.add('idle-float');
      flying = false;
      open = false;
    }, 750);
  }

  return { init, close, isOpen: () => open, setReadyCheck };
})();
