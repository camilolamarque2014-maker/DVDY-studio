// DVDY Studio · sitio web. Movimiento según ux-motion: respuesta inmediata, entradas con ease-out,
// salidas más rápidas que las entradas, todo interrumpible y respetando «reducir movimiento».
(() => {
  const REPO = "camilolamarque2014-maker/DVDY-studio";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;

  // ---------- Versión y enlace directo desde el último release de GitHub ----------
  fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((rel) => {
      const zip = (rel.assets || []).find((a) => a.name.toLowerCase().endsWith(".zip"));
      const mb = zip ? Math.round(zip.size / 1048576) : null;
      document.querySelectorAll(".js-version").forEach((el) => {
        el.textContent = `Versión ${rel.tag_name.replace(/^v/i, "")}` + (mb ? ` · ${mb} MB` : "");
      });
      if (zip) document.querySelectorAll(".js-download").forEach((a) => (a.href = zip.browser_download_url));
    })
    .catch(() => { /* sin conexión: los botones llevan a la página de releases */ });

  // ---------- Botón Descargar: respuesta en menos de 100 ms y un final claro ----------
  document.querySelectorAll(".js-download").forEach((btn) => {
    let timers = [];
    btn.addEventListener("click", () => {
      timers.forEach(clearTimeout);
      const text = btn.querySelector(".btn-text");
      btn.classList.add("is-going");
      text.textContent = "Descargando…";
      timers = [
        setTimeout(() => (text.textContent = "Listo: revisa tus descargas"), 650),
        setTimeout(() => { btn.classList.remove("is-going"); text.textContent = btn.dataset.label; }, 6000),
      ];
    });
  });

  // ---------- Aparición al desplazarse (una sola vez, en cascada de 40 ms) ----------
  const groups = document.querySelectorAll("[data-reveal], [data-stagger]");
  document.querySelectorAll("[data-stagger]").forEach((g) => {
    // Pasados 6 elementos, el resto entra junto para no hacer esperar
    [...g.children].forEach((c, i) => c.style.setProperty("--i", Math.min(i, 5)));
  });
  if (reduce || !("IntersectionObserver" in window)) {
    groups.forEach((g) => g.classList.add("is-in"));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
    groups.forEach((g) => io.observe(g));
  }

  // ---------- La demo del dial ----------
  const scale = document.querySelector(".dial-demo .scale");
  if (scale) {
    const ns = "http://www.w3.org/2000/svg";
    const ticks = scale.querySelector(".ticks");
    const nums = scale.querySelector(".nums");
    const L = 10, R = 390, BASE = 36;
    for (let i = 0; i <= 40; i++) {
      const x = L + ((R - L) * i) / 40;
      const major = i % 10 === 0;
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", x); line.setAttribute("x2", x);
      line.setAttribute("y1", BASE - (major ? 16 : i % 5 === 0 ? 10 : 6)); line.setAttribute("y2", BASE);
      if (major) line.setAttribute("class", "major");
      ticks.appendChild(line);
      if (major) {
        const t = document.createElementNS(ns, "text");
        t.setAttribute("x", x); t.setAttribute("y", BASE + 14);
        t.textContent = String((i / 40) * 100);
        nums.appendChild(t);
      }
    }
    const needle = scale.querySelector(".needle");
    const row = document.querySelector(".dial-demo .row.is-active");
    const status = row.querySelector(".js-status");
    const bar = row.querySelector(".js-bar");
    const count = document.querySelector(".js-dial-count");
    const setProgress = (p) => {
      needle.setAttribute("transform", `translate(${(R - L) * p}, 0)`);
      bar.style.transform = `scaleX(${p})`;
      status.textContent = `Bajando ${Math.round(p * 100)} %  ·  2,4 MB/s`;
    };
    const finish = () => {
      row.classList.add("is-done");
      scale.classList.add("is-idle");
      status.textContent = "Listo · Me at the zoo.mp4";
      count.textContent = "2 listas";
    };
    const run = () => {
      if (reduce) { setProgress(1); finish(); return; }
      const DURATION = 2600; // la descarga de la demo: lineal, como una barra de progreso real
      let start = null;
      const step = (ts) => {
        if (start === null) start = ts;
        // pequeños escalones, como llegan los datos de una descarga
        const p = Math.min(1, Math.floor(((ts - start) / DURATION) * 40) / 40);
        setProgress(p);
        if (p < 1) requestAnimationFrame(step); else setTimeout(finish, 120);
      };
      requestAnimationFrame(step);
    };
    setProgress(0);
    const demo = document.querySelector(".dial-demo");
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((e) => {
        if (e[0].isIntersecting) { io.disconnect(); setTimeout(run, reduce ? 0 : 500); }
      }, { threshold: 0.4 });
      io.observe(demo);
    } else run();
  }

  // ---------- Inclinación de la captura hacia el puntero ----------
  const shot = document.querySelector(".shot-wide");
  if (shot && finePointer && !reduce) {
    shot.addEventListener("pointermove", (e) => {
      const r = shot.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      shot.style.setProperty("--ry", `${(x * 6).toFixed(2)}deg`);
      shot.style.setProperty("--rx", `${(-y * 4).toFixed(2)}deg`);
    });
    shot.addEventListener("pointerleave", () => {
      shot.style.setProperty("--ry", "0deg");
      shot.style.setProperty("--rx", "0deg");
    });
  }

  // ---------- Selector de funciones (banda) ----------
  const tabs = [...document.querySelectorAll('.band [role="tab"]')];
  const img = document.querySelector(".js-feature-img");
  const texts = [...document.querySelectorAll(".ft")];
  let pending = [];
  const ALT = {
    descargar: "Pantalla Descargar con una descarga terminada y los botones Abrir y Mostrar en la carpeta.",
    convertir: "Pantalla Convertir en modo Simple: lista de archivos y la opción Convertir a.",
    herramientas: "Pantalla Herramientas con las utilidades agrupadas y el formulario de Recortar fragmento.",
    avanzado: "Pantalla Descargar en modo Avanzado con todas las opciones desplegadas.",
  };
  const select = (tab, focus) => {
    if (tab.getAttribute("aria-selected") === "true") return;
    pending.forEach(clearTimeout); pending = []; // interrumpible: un clic nuevo cancela el anterior
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
    });
    if (focus) tab.focus();
    tab.classList.add("pop");
    pending.push(setTimeout(() => tab.classList.remove("pop"), 150));

    const key = tab.dataset.text;
    const next = texts.find((t) => t.dataset.key === key);
    const current = texts.find((t) => !t.hidden && t !== next);
    const showNext = () => {
      texts.forEach((t) => { t.hidden = t !== next; t.classList.remove("is-leaving"); });
      next.classList.add("is-entering");
      requestAnimationFrame(() => requestAnimationFrame(() => next.classList.remove("is-entering")));
    };
    if (current && !reduce) {
      current.classList.add("is-leaving"); // sale más rápido de lo que entra (110 ms contra 200 ms)
      pending.push(setTimeout(showNext, 110));
    } else showNext();

    const src = `assets/img/${tab.dataset.shot}.webp`;
    img.classList.add("is-swapping");
    pending.push(setTimeout(() => {
      img.onload = () => img.classList.remove("is-swapping");
      img.src = src;
      img.alt = ALT[key];
    }, reduce ? 0 : 100));
  };
  tabs.forEach((t, i) => {
    t.tabIndex = i === 0 ? 0 : -1;
    t.addEventListener("click", () => select(t));
    t.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      select(tabs[(i + d + tabs.length) % tabs.length], true);
    });
  });
  if (img) img.alt = ALT.descargar;
  // Precargar las otras capturas para que el cambio responda al instante (umbral de Doherty)
  if ("requestIdleCallback" in window) {
    requestIdleCallback(() => tabs.forEach((t) => { const i = new Image(); i.src = `assets/img/${t.dataset.shot}.webp`; }));
  }
})();
