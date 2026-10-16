/*
 * The explanatory layer, shared by every page (loaded after i18n.js and glossary.js).
 *
 *   - Explainers: any <button class="term" data-term="rps"> opens a short explanation from glossary.js,
 *     next to the word on wide screens and as a sheet from the bottom on phones.
 *   - On the deep dives (pages with <article class="post">):
 *       reading depth (Quick take / Full analysis / Nerd mode). Mark up blocks with
 *         data-show="quick"      only in the quick take (a summary that stands in for the full text),
 *         data-show="full"       in the full analysis and in nerd mode,
 *         data-show="nerd"       only in nerd mode (code, model internals),
 *         data-show="full-only"  only in the full analysis (for example a "show the code" button);
 *       blocks can be nested, and a link or address to a hidden block switches to a depth that shows it;
 *       a contents list built from the headings, sticky beside the text on wide screens;
 *       a reading-progress line under the top bar;
 *       an "Enlarge chart" button on phones that opens a chart at a readable size.
 */
(() => {
  "use strict";

  const { t } = window.I18N;
  const GLOSSARY = window.GLOSSARY;
  const ROOT = new URL(".", document.currentScript.src);
  const DEPTH_KEY = "jans-matchday:depth";
  const DEPTHS = ["quick", "full", "nerd"];
  const SHOWN_AT = { quick: ["quick"], full: ["full", "nerd"], nerd: ["nerd"], "full-only": ["full"] };
  const phone = window.matchMedia("(max-width: 720px)");

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---------- Explainers ---------- */

  const panel = element("div", "explainer");
  panel.id = "explainer";
  panel.hidden = true;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-labelledby", "explainer-title");
  const backdrop = element("div", "explainer-backdrop");
  backdrop.hidden = true;
  let openTerm = null;

  function entryFor(id) {
    return GLOSSARY?.[window.I18N.lang]?.[id] ?? GLOSSARY?.en?.[id] ?? null;
  }

  function fillPanel(id) {
    const entry = entryFor(id);
    if (!entry) return false;
    const head = element("div", "explainer-head");
    head.append(element("p", "explainer-kicker", t("explain.label")));
    const close = element("button", "explainer-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", t("explain.close"));
    close.addEventListener("click", () => closePanel(true));
    head.append(close);
    const title = element("h2", "explainer-title", entry.term);
    title.id = "explainer-title";
    const body = element("p", "explainer-text", entry.short);
    const read = element("p", "explainer-read");
    read.append(element("strong", "", `${t("explain.howToRead")} `), entry.read);
    const link = element("a", "explainer-link", t("explain.glossaryLink"));
    link.href = new URL(`learn/#${id}`, ROOT).href;
    panel.replaceChildren(head, title, body, read, link);
    return true;
  }

  function placePanel(button) {
    if (phone.matches) {
      panel.classList.add("is-sheet");
      panel.style.left = "";
      panel.style.top = "";
      backdrop.hidden = false;
      return;
    }
    panel.classList.remove("is-sheet");
    backdrop.hidden = true;
    const box = button.getBoundingClientRect();
    const width = Math.min(360, document.documentElement.clientWidth - 32);
    const left = Math.max(16, Math.min(box.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - width - 16));
    panel.style.left = `${left}px`;
    panel.style.top = `${box.bottom + window.scrollY + 8}px`;
  }

  function openPanel(button) {
    if (!fillPanel(button.dataset.term)) return;
    if (openTerm && openTerm !== button) openTerm.setAttribute("aria-expanded", "false");
    openTerm = button;
    button.setAttribute("aria-expanded", "true");
    button.setAttribute("aria-controls", "explainer");
    panel.hidden = false;
    placePanel(button);
    panel.querySelector(".explainer-close").focus({ preventScroll: true });
  }

  function closePanel(returnFocus) {
    if (panel.hidden) return;
    panel.hidden = true;
    backdrop.hidden = true;
    if (openTerm) {
      openTerm.setAttribute("aria-expanded", "false");
      if (returnFocus) openTerm.focus({ preventScroll: true });
    }
    openTerm = null;
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".term[data-term]");
    if (button) {
      event.preventDefault();
      if (openTerm === button && !panel.hidden) closePanel(true);
      else openPanel(button);
      return;
    }
    if (!panel.hidden && !panel.contains(event.target)) closePanel(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) closePanel(true);
  });
  window.addEventListener("resize", () => { if (openTerm && !panel.hidden) placePanel(openTerm); });

  /* ---------- Deep dives: reading depth, contents, progress, charts ---------- */

  const posts = [...document.querySelectorAll("article.post")];

  function readStoredDepth() {
    try {
      const value = localStorage.getItem(DEPTH_KEY);
      return DEPTHS.includes(value) ? value : "full";
    } catch {
      return "full";
    }
  }

  function storeDepth(value) {
    try {
      localStorage.setItem(DEPTH_KEY, value);
    } catch {
      // Private mode: the choice lasts for this visit.
    }
  }

  let depth = readStoredDepth();

  // The depths at which a node is shown, from every data-show block around it.
  function levelsFor(node, within) {
    let levels = DEPTHS;
    for (let block = node.closest("[data-show]"); block && within.contains(block); block = block.parentElement?.closest("[data-show]")) {
      const allowed = SHOWN_AT[block.dataset.show] ?? DEPTHS;
      levels = levels.filter((level) => allowed.includes(level));
    }
    return levels;
  }

  // Reading time for each depth, from the words that depth shows (about 220 words a minute),
  // plus about 12 seconds per chart and 15 per code block.
  function minutesFor(post, level) {
    const body = post.querySelector(".post-body");
    let words = 0;
    for (const node of body.querySelectorAll("p, li, figcaption, td, h2, h3")) {
      if (node.closest(".depth-switch, .post-toc, .depth-peek, .howto")) continue;
      if (levelsFor(node, body).includes(level)) words += node.textContent.trim().split(/\s+/).length;
    }
    for (const figure of body.querySelectorAll(".post-figure")) {
      if (levelsFor(figure, body).includes(level)) words += 44;
    }
    for (const code of body.querySelectorAll("pre")) {
      if (levelsFor(code, body).includes(level)) words += 55;
    }
    return Math.max(1, Math.round(words / 220));
  }

  // A link or an address (#verdict) can point into a block the current depth hides: switch to one that shows it.
  function reveal(target) {
    const post = target?.closest("article.post");
    if (!post) return false;
    const levels = levelsFor(target, post);
    if (!levels.length || levels.includes(depth)) return false;
    applyDepth(levels.includes("full") ? "full" : levels[0]);
    return true;
  }

  function targetOf(hash) {
    try {
      const id = decodeURIComponent(hash.replace(/^#/, ""));
      return id ? document.getElementById(id) : null;
    } catch {
      return null;
    }
  }

  function goTo(target) {
    if (!target) return;
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  }

  function buildDepthSwitch(post) {
    const group = element("div", "depth-switch");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", t("depth.label"));
    for (const level of DEPTHS) {
      const button = element("button", "depth-button");
      button.type = "button";
      button.dataset.depth = level;
      button.append(element("span", "depth-name", t(`depth.${level}`)), element("span", "depth-time", t("depth.minutes", { count: minutesFor(post, level) })));
      group.append(button);
    }
    return group;
  }

  function buildToc(post) {
    const headings = [...post.querySelectorAll(".post-body h2")].filter((heading) => heading.offsetParent !== null && !heading.closest(".post-sources"));
    const list = element("ol", "post-toc-list");
    headings.forEach((heading, index) => {
      if (!heading.id) heading.id = `${post.lang}-section-${index + 1}`;
      const item = element("li");
      const link = element("a", "", heading.textContent.replace(/\s+/g, " ").trim());
      link.href = `#${heading.id}`;
      link.dataset.target = heading.id;
      item.append(link);
      list.append(item);
    });
    return list;
  }

  function renderToc(post) {
    const toc = post.querySelector(".post-toc");
    if (!toc) return;
    toc.querySelector(".post-toc-list")?.replaceWith(buildToc(post));
  }

  function applyDepth(next, { focus } = {}) {
    depth = next;
    for (const post of posts) {
      post.dataset.depth = depth;
      for (const button of post.querySelectorAll(".depth-button")) {
        button.setAttribute("aria-pressed", String(button.dataset.depth === depth));
      }
      renderToc(post);
    }
    if (focus) focus.focus({ preventScroll: true });
    updateProgress();
  }

  // The article template ships the layout, the contents column and the depth switch in its HTML, so nothing
  // jumps when this runs; older markup without them still gets them here.
  function enhancePost(post) {
    const body = post.querySelector(".post-body");
    if (!body) return;
    if (!post.querySelector(".post-layout")) {
      const layout = element("div", "post-layout");
      const toc = element("nav", "post-toc");
      toc.setAttribute("aria-label", t("toc.title"));
      toc.append(element("p", "post-toc-title", t("toc.title")), element("ol", "post-toc-list"));
      body.before(layout);
      layout.append(toc, body);
    }
    const fresh = buildDepthSwitch(post);
    const current = body.querySelector(".depth-switch");
    if (current) current.replaceWith(fresh);
    else body.prepend(fresh);

    for (const figure of body.querySelectorAll(".post-figure")) {
      const image = figure.querySelector("img");
      if (!image || figure.querySelector(".figure-enlarge")) continue;
      const open = () => openViewer(image, figure.querySelector("figcaption"));
      const button = element("button", "figure-enlarge", t("figure.enlarge"));
      button.type = "button";
      button.addEventListener("click", open);
      image.addEventListener("click", () => { if (phone.matches) open(); });
      const howto = figure.querySelector(".howto");
      if (howto) howto.before(button);
      else figure.append(button);
    }
  }

  function relabel() {
    for (const post of posts) {
      const old = post.querySelector(".depth-switch");
      if (old) old.replaceWith(buildDepthSwitch(post));
      const toc = post.querySelector(".post-toc");
      if (toc) {
        toc.setAttribute("aria-label", t("toc.title"));
        toc.querySelector(".post-toc-title").textContent = t("toc.title");
      }
      post.querySelectorAll(".figure-enlarge").forEach((button) => { button.textContent = t("figure.enlarge"); });
    }
    applyDepth(depth);
  }

  /* Reading progress and the current section in the contents. */
  const progress = element("div", "reading-progress");
  progress.setAttribute("aria-hidden", "true");
  let ticking = false;

  function visiblePost() {
    return posts.find((post) => !post.hidden) ?? null;
  }

  function updateProgress() {
    ticking = false;
    const post = visiblePost();
    if (!post) return;
    const box = post.getBoundingClientRect();
    const total = box.height - window.innerHeight;
    const done = total > 0 ? Math.min(1, Math.max(0, -box.top / total)) : 1;
    progress.style.transform = `scaleX(${done})`;
    let current = null;
    for (const link of post.querySelectorAll(".post-toc a")) {
      const heading = document.getElementById(link.dataset.target);
      if (heading && heading.getBoundingClientRect().top < window.innerHeight * 0.3) current = link;
    }
    post.querySelectorAll(".post-toc a").forEach((link) => {
      if (link === current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }

  /* A chart at a readable size on phones. */
  const viewer = element("dialog", "figure-viewer");
  function openViewer(image, caption) {
    const close = element("button", "figure-viewer-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", t("figure.close"));
    close.addEventListener("click", () => viewer.close());
    const scroller = element("div", "figure-viewer-scroll");
    const copy = image.cloneNode();
    copy.removeAttribute("loading");
    scroller.append(copy);
    viewer.replaceChildren(close, scroller, element("p", "figure-viewer-hint", t("figure.hint")));
    if (caption) viewer.append(element("p", "figure-viewer-caption", caption.textContent));
    viewer.setAttribute("aria-label", image.alt || t("figure.enlarge"));
    viewer.showModal();
    close.focus();
  }
  viewer.addEventListener("click", (event) => { if (event.target === viewer) viewer.close(); });

  /* ---------- Start ---------- */

  document.body.append(backdrop, panel);
  backdrop.addEventListener("click", () => closePanel(true));

  if (posts.length) {
    posts.forEach(enhancePost);
    document.querySelector(".topbar")?.append(progress);
    document.body.append(viewer);
    document.addEventListener("click", (event) => {
      const button = event.target.closest(".depth-button");
      if (button) {
        storeDepth(button.dataset.depth);
        applyDepth(button.dataset.depth, { focus: button.closest(".post").querySelector(`.depth-button[data-depth="${button.dataset.depth}"]`) });
      }
      const show = event.target.closest("[data-set-depth]");
      if (show) {
        storeDepth(show.dataset.setDepth);
        applyDepth(show.dataset.setDepth);
        if (show.dataset.scrollTo) goTo(document.getElementById(show.dataset.scrollTo));
      }
      // In-page links: show the target first, then let the browser scroll to it as usual.
      const link = event.target.closest('a[href^="#"]');
      if (link) reveal(targetOf(link.getAttribute("href")));
    });
    window.addEventListener("hashchange", () => {
      const target = targetOf(location.hash);
      if (reveal(target)) goTo(target);
    });
    window.addEventListener("scroll", () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(updateProgress);
      }
    }, { passive: true });
    applyDepth(depth);
    const target = targetOf(location.hash);
    if (reveal(target)) requestAnimationFrame(() => goTo(target));
  }

  window.I18N.onChange(() => {
    if (posts.length) relabel();
    if (openTerm && !panel.hidden) fillPanel(openTerm.dataset.term);
  });

  window.EXPLAIN = { open: openPanel, close: closePanel, get depth() { return depth; } };
})();
