/* Learner DNA — dedicated landscape visualization.
 *
 * Orientation: the double-helix runs horizontally (along X), not
 * vertically, so the composition reads as a wide cinematic strip rather
 * than a portrait/mobile DNA card, per the brief.
 *
 * Data honesty: setProgress(readinessScore, hasAssessment) is the ONLY
 * way this module's "lit" state changes. When hasAssessment is false the
 * DNA is forced into a deep-dormant state regardless of any other number
 * in scope — a brand-new learner must never see fabricated illumination.
 * There is no local fallback progress value baked in here.
 */
const DNA = (function () {
  let scene, camera, renderer, group, branchGroup, dust, pMat;
  let lineA, lineB, rungGeo, rungMat, branchMat, branchGeo;
  let strandAPts = [], strandBPts = [];
  let pInfo = [];
  let wrap, canvas;
  let ready = false;

  const SEGMENTS = 110;
  const RADIUS = 1.9;
  const LENGTH = 15.5;   // runs along X — the landscape dimension
  const TURNS = 4.2;
  const PCOUNT = 260;

  const DIM = { r: 0.06, g: 0.05, b: 0.035 };   // near-black, barely-there gold
  const GOLD = { r: 0.851, g: 0.663, b: 0.306 }; // #d9a94e
  const GOLD_HOT = { r: 1.0, g: 0.89, b: 0.627 };

  let progress = 0.03;
  let hasAssessment = false;
  let flashUntil = 0;
  let elapsed = 0;

  function strandPoint(i, offset) {
    const t = i / SEGMENTS;
    const angle = t * Math.PI * 2 * TURNS + offset;
    return new THREE.Vector3((t - 0.5) * LENGTH, Math.cos(angle) * RADIUS, Math.sin(angle) * RADIUS);
  }

  function makeStrandLine(pts) {
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const colors = new Float32Array(pts.length * 3);
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const mat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.9 });
    return new THREE.Line(geo, mat);
  }

  function makeGlowSprite() {
    const size = 64;
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const ctx = c.getContext('2d');
    const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, 'rgba(255,227,160,1)');
    grad.addColorStop(0.4, 'rgba(217,169,78,0.7)');
    grad.addColorStop(1, 'rgba(217,169,78,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
    return new THREE.CanvasTexture(c);
  }

  function buildBranch(origin, dir, length, depth, positions) {
    if (depth <= 0 || length < 0.15) return;
    const segments = 4;
    let cur = origin.clone();
    let curDir = dir.clone();
    for (let s = 0; s < segments; s++) {
      const next = cur.clone().add(curDir.clone().multiplyScalar(length / segments));
      next.x += (Math.random() - 0.5) * length * 0.16;
      next.y += (Math.random() - 0.5) * length * 0.22;
      next.z += (Math.random() - 0.5) * length * 0.16;
      positions.push(cur.x, cur.y, cur.z, next.x, next.y, next.z);
      cur = next;
      curDir.y += (Math.random() - 0.5) * 0.35;
      curDir.z += (Math.random() - 0.5) * 0.3;
      curDir.normalize();
    }
    const children = depth > 1 ? 2 + Math.floor(Math.random() * 2) : 0;
    for (let c = 0; c < children; c++) {
      const spread = 0.9;
      const childDir = curDir.clone();
      childDir.x += (Math.random() - 0.5) * spread * 0.6;
      childDir.y += (Math.random() - 0.5) * spread;
      childDir.z += (Math.random() - 0.5) * spread;
      childDir.normalize();
      buildBranch(cur, childDir, length * 0.62, depth - 1, positions);
    }
  }

  function paint() {
    const litCount = Math.floor(SEGMENTS * progress);
    function paintStrand(line, pts) {
      const colorAttr = line.geometry.attributes.color;
      for (let i = 0; i < pts.length; i++) {
        const c = i < litCount ? lerpColor(DIM, GOLD, Math.min(1, progress * 1.4)) : DIM;
        colorAttr.setXYZ(i, c.r, c.g, c.b);
      }
      colorAttr.needsUpdate = true;
    }
    paintStrand(lineA, strandAPts);
    paintStrand(lineB, strandBPts);
    const rc = rungGeo.attributes.color;
    for (let i = 0; i < SEGMENTS; i += 2) {
      const c = i < litCount ? lerpColor(DIM, GOLD, Math.min(1, progress * 1.4)) : DIM;
      rc.setXYZ(i, c.r, c.g, c.b); rc.setXYZ(i + 1, c.r, c.g, c.b);
    }
    rc.needsUpdate = true;
    branchMat.opacity = 0.28 + progress * 0.3;
    const bc = lerpColor(DIM, GOLD, progress * 0.4);
    branchMat.color.setRGB(bc.r, bc.g, bc.b);
  }

  function lerpColor(a, b, t) {
    return { r: a.r + (b.r - a.r) * t, g: a.g + (b.g - a.g) * t, b: a.b + (b.b - a.b) * t };
  }

  function init(wrapId, canvasId) {
    wrap = document.getElementById(wrapId);
    canvas = document.getElementById(canvasId);
    if (!wrap || !canvas || ready) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(38, wrap.clientWidth / Math.max(wrap.clientHeight, 1), 0.1, 100);
    camera.position.set(0, 0.4, 15.5);
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);

    group = new THREE.Group();
    scene.add(group);

    strandAPts = []; strandBPts = [];
    for (let i = 0; i <= SEGMENTS; i++) {
      strandAPts.push(strandPoint(i, 0));
      strandBPts.push(strandPoint(i, Math.PI));
    }
    lineA = makeStrandLine(strandAPts);
    lineB = makeStrandLine(strandBPts);
    group.add(lineA, lineB);

    rungGeo = new THREE.BufferGeometry();
    const rungPositions = new Float32Array(SEGMENTS * 6);
    for (let i = 0; i < SEGMENTS; i += 2) {
      const a = strandAPts[i], b = strandBPts[i];
      rungPositions[i * 6 + 0] = a.x; rungPositions[i * 6 + 1] = a.y; rungPositions[i * 6 + 2] = a.z;
      rungPositions[i * 6 + 3] = b.x; rungPositions[i * 6 + 4] = b.y; rungPositions[i * 6 + 5] = b.z;
    }
    rungGeo.setAttribute('position', new THREE.BufferAttribute(rungPositions, 3));
    rungGeo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(SEGMENTS * 6), 3));
    rungMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55 });
    group.add(new THREE.LineSegments(rungGeo, rungMat));

    // Flowing gold particle motes
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(PCOUNT * 3);
    pInfo = [];
    for (let i = 0; i < PCOUNT; i++) {
      const baseR = 2.6 + Math.random() * 3.2;
      const theta = Math.random() * Math.PI * 2;
      const x0 = (Math.random() - 0.5) * LENGTH * 1.35;
      pInfo.push({
        baseR, theta, x0,
        thetaSpeed: (Math.random() - 0.5) * 0.07,
        xSpeed: (Math.random() * 0.35 + 0.1) * (Math.random() < 0.5 ? 1 : -1),
        phase: Math.random() * Math.PI * 2,
      });
      pPos[i * 3] = x0; pPos[i * 3 + 1] = Math.cos(theta) * baseR; pPos[i * 3 + 2] = Math.sin(theta) * baseR;
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    pMat = new THREE.PointsMaterial({
      map: makeGlowSprite(), color: 0xd9a94e, size: 0.15, transparent: true,
      opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    dust = new THREE.Points(pGeo, pMat);
    group.add(dust);

    // Organic nerve / root branch network — spreads behind + around the
    // helix along the horizontal axis, echoing tree-limb / root growth.
    branchGroup = new THREE.Group();
    scene.add(branchGroup);
    const branchPositions = [];
    const ROOT_COUNT = 7;
    for (let i = 0; i < ROOT_COUNT; i++) {
      const side = i % 2 === 0 ? 1 : -1;
      const x = (i / ROOT_COUNT - 0.5) * LENGTH * 1.4;
      const origin = new THREE.Vector3(x, -side * 1.5 + (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 3);
      const dir = new THREE.Vector3((Math.random() - 0.5) * 0.4, side * 0.8, (Math.random() - 0.5) * 0.6).normalize();
      buildBranch(origin, dir, 2.8, 4, branchPositions);
    }
    branchGeo = new THREE.BufferGeometry();
    branchGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(branchPositions), 3));
    branchMat = new THREE.LineBasicMaterial({ color: 0x1c160d, transparent: true, opacity: 0.28 });
    branchGroup.add(new THREE.LineSegments(branchGeo, branchMat));
    branchGroup.scale.setScalar(1.05);

    paint();

    const clock = new THREE.Clock();
    function animate() {
      requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      elapsed += dt;
      group.rotation.y = Math.sin(elapsed * 0.06) * 0.35; // slow gentle sway, not a full spin — keeps landscape read stable
      group.rotation.x = Math.sin(elapsed * 0.04) * 0.05;

      const posAttr = dust.geometry.attributes.position;
      for (let i = 0; i < PCOUNT; i++) {
        const info = pInfo[i];
        let x = info.x0 + elapsed * info.xSpeed;
        const span = LENGTH * 1.35;
        x = ((x + span / 2) % span + span) % span - span / 2;
        const theta = info.theta + elapsed * info.thetaSpeed;
        const r = info.baseR + Math.sin(elapsed * 0.6 + info.phase) * 0.22;
        posAttr.setXYZ(i, x, Math.cos(theta) * r, Math.sin(theta) * r);
      }
      posAttr.needsUpdate = true;

      branchGroup.rotation.y = Math.sin(elapsed * 0.03) * 0.12;

      if (performance.now() < flashUntil) {
        const s = 1 + Math.sin(performance.now() * 0.02) * 0.035;
        group.scale.setScalar(s);
        pMat.opacity = Math.min(0.9, 0.35 + progress * 0.6);
      } else {
        group.scale.setScalar(1);
        pMat.opacity = 0.18 + progress * 0.55;
      }
      renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', resize);
    ready = true;
  }

  function resize() {
    if (!wrap || !renderer) return;
    camera.aspect = wrap.clientWidth / Math.max(wrap.clientHeight, 1);
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  }

  /**
   * readinessScore: real 0-100 number from GET /api/engines/readiness.
   * assessed: real boolean derived from the learner's assessment_status
   *  / missing_evidence — NOT a guess. When false, the DNA stays dormant
   *  no matter what readinessScore says (it will be 0 anyway, but this
   *  keeps the visual honest even if that ever changes upstream).
   */
  function setProgress(readinessScore, assessed) {
    hasAssessment = !!assessed;
    if (!hasAssessment) {
      progress = 0.03; // near-fully dormant, a hint of latent gold only
    } else {
      progress = 0.08 + Math.min(1, Math.max(0, readinessScore) / 100) * 0.62;
    }
    if (ready) paint();
  }

  function pulse() {
    flashUntil = performance.now() + 900;
  }

  return { init, setProgress, pulse, resize };
})();
