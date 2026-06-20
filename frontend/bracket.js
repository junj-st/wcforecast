// Bracket view: current group tables + projected Round-of-32, with team highlight.
const Bracket = (function () {
  const API = location.origin.startsWith("http") ? location.origin : "http://localhost:8000";
  let loaded = false;

  async function ensureLoaded() {
    if (loaded) return;
    loaded = true;
    await Promise.all([renderGroups(), renderR32()]);
    wireHighlight();
  }

  async function renderGroups() {
    const d = await (await fetch(`${API}/standings`)).json();
    const grid = document.getElementById("groups");
    grid.innerHTML = Object.keys(d).sort().map(letter => {
      const rows = d[letter].map(r => `
        <div class="group-row ${r.position <= 2 ? "q" + r.position : ""}" data-team="${r.canonical}">
          <span class="pos">${r.position}</span>
          <span class="name"><span class="dot" style="background:${teamColor(r.canonical)}"></span>${r.team}</span>
          <span class="pts">${r.points}</span>
          <span class="gd">${r.played ? (r.goal_difference > 0 ? "+" : "") + r.goal_difference : "·"}</span>
        </div>`).join("");
      return `<div class="group-card"><h3>GROUP ${letter}</h3>${rows}</div>`;
    }).join("");
  }

  async function renderR32() {
    const d = await (await fetch(`${API}/bracket`)).json();
    const grid = document.getElementById("r32");
    grid.innerHTML = d.round_of_32.map(m => `
      <div class="tie">
        <div class="mno">Match ${m.match}</div>
        <div class="side" data-team="${m.home_canonical || ""}">
          <span><span class="dot" style="background:${teamColor(m.home_canonical)}"></span>${m.home || "TBD"}</span><span class="slot">${m.home_slot}</span>
        </div>
        <div class="side" data-team="${m.away_canonical || ""}">
          <span><span class="dot" style="background:${teamColor(m.away_canonical)}"></span>${m.away || "TBD"}</span><span class="slot">${m.away_slot}</span>
        </div>
      </div>`).join("");
  }

  function wireHighlight() {
    let active = null;
    document.querySelectorAll("[data-team]").forEach(el => {
      el.addEventListener("click", () => {
        const team = el.dataset.team;
        const on = team !== active;
        document.querySelectorAll(".highlight").forEach(e => e.classList.remove("highlight"));
        if (on) {
          document.querySelectorAll(`[data-team="${CSS.escape(team)}"]`)
            .forEach(e => e.classList.add("highlight"));
        }
        active = on ? team : null;
      });
    });
  }

  return { ensureLoaded };
})();
