// Probability dashboard: title-odds bar chart + sortable, heatmap-shaded table.
const API_BASE = location.origin.startsWith("http") ? location.origin : "http://localhost:8000";

let simData = null;
let sortKey = "WINNER";
let sortDir = -1;
let titleChart = null;

const groupOf = {}; // canonical -> group letter, from /teams

function probColor(p) {
  // transparent teal -> solid teal as probability rises
  const a = Math.min(1, Math.max(0, p));
  return `rgba(54, 194, 164, ${0.08 + a * 0.92})`;
}

function fmtPct(p) {
  if (p >= 0.995) return "100%";
  if (p < 0.005) return "—";
  return (p * 100).toFixed(1) + "%";
}

async function loadGroups() {
  const r = await fetch(`${API_BASE}/teams`);
  const d = await r.json();
  d.teams.forEach(t => { groupOf[t.canonical] = (t.group || "").replace("GROUP_", ""); });
  document.getElementById("meta").textContent =
    `Live data fetched ${ (d.fetched_at || "").slice(0,10) } · season ${d.season}`;
}

async function runSimulation() {
  const n = document.getElementById("nSims").value;
  const status = document.getElementById("simStatus");
  const btn = document.getElementById("runSim");
  btn.disabled = true;
  status.textContent = `Simulating ${(+n).toLocaleString()} tournaments…`;
  try {
    const r = await fetch(`${API_BASE}/simulate?n=${n}`);
    simData = await r.json();
    status.textContent = `${simData.n_simulations.toLocaleString()} simulations`;
    renderChart();
    renderTable();
  } catch (e) {
    status.textContent = "Error — is the API running? (uvicorn backend.main:app)";
  } finally {
    btn.disabled = false;
  }
}

function sortedTeams() {
  const rows = simData.teams.slice();
  rows.sort((a, b) => {
    let va = sortKey === "group" ? (groupOf[a.canonical] || "") :
             sortKey === "name" ? a.name : a[sortKey];
    let vb = sortKey === "group" ? (groupOf[b.canonical] || "") :
             sortKey === "name" ? b.name : b[sortKey];
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });
  return rows;
}

function renderTable() {
  const rows = sortedTeams();
  const stages = ["R32", "R16", "QF", "SF", "FINAL", "WINNER"];
  const tbody = document.querySelector("#probTable tbody");
  tbody.innerHTML = rows.map(t => `
    <tr>
      <td class="left team">${t.name}</td>
      <td class="left">${groupOf[t.canonical] || ""}</td>
      ${stages.map(s => {
        const p = t[s];
        return `<td><span class="prob-cell" style="background:${probColor(p)};padding:2px 6px;">${fmtPct(p)}</span></td>`;
      }).join("")}
    </tr>`).join("");
  document.querySelectorAll("#probTable th").forEach(th => {
    th.classList.toggle("sorted", th.dataset.key === sortKey);
  });
}

function renderChart() {
  const top = simData.teams.slice().sort((a, b) => b.WINNER - a.WINNER).slice(0, 12);
  const ctx = document.getElementById("titleChart");
  if (titleChart) titleChart.destroy();
  titleChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map(t => t.name),
      datasets: [{
        data: top.map(t => +(t.WINNER * 100).toFixed(1)),
        backgroundColor: "rgba(54,194,164,0.8)",
        borderRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => `${c.parsed.y}% to win` } } },
      scales: {
        y: { ticks: { color: "#8b98a5", callback: v => v + "%" }, grid: { color: "#2e3a46" } },
        x: { ticks: { color: "#e6edf3" }, grid: { display: false } },
      },
    },
  });
}

document.querySelectorAll("#probTable th").forEach(th => {
  th.addEventListener("click", () => {
    const key = th.dataset.key;
    if (sortKey === key) sortDir *= -1;
    else { sortKey = key; sortDir = (key === "name" || key === "group") ? 1 : -1; }
    renderTable();
  });
});

document.getElementById("runSim").addEventListener("click", runSimulation);

(async function init() {
  await loadGroups();
  await runSimulation();
})();
