// Signature national-team colors, keyed by canonical team name (see data/aliases.py).
// Used to color chart bars and the swatch next to each team name.
const TEAM_COLORS = {
  "czechia": "#D7141A",
  "mexico": "#006341",
  "south africa": "#007A4D",
  "south korea": "#C8102E",
  "bosnia and herzegovina": "#002F6C",
  "canada": "#D52B1E",
  "qatar": "#8A1538",
  "switzerland": "#D52B1E",
  "brazil": "#F7D117",
  "haiti": "#00209F",
  "morocco": "#C1272D",
  "scotland": "#0B4EA2",
  "australia": "#FFCD00",
  "paraguay": "#D52B1E",
  "turkey": "#E30A17",
  "usa": "#0A3161",
  "curacao": "#002B7F",
  "ecuador": "#FFD100",
  "germany": "#E9E9E9",
  "ivory coast": "#F77F00",
  "japan": "#002D9C",          // samurai blue
  "netherlands": "#EC7000",    // oranje
  "sweden": "#FECC00",
  "tunisia": "#E70013",
  "belgium": "#ED2939",
  "egypt": "#CE1126",
  "iran": "#2E8B57",
  "new zealand": "#DDDDDD",
  "cape verde islands": "#003893",
  "saudi arabia": "#006C35",
  "spain": "#C60B1E",          // la roja
  "uruguay": "#5CBFEB",        // celeste
  "france": "#002395",
  "iraq": "#007A3D",
  "norway": "#BA0C2F",
  "senegal": "#00853F",
  "algeria": "#007229",
  "argentina": "#75AADB",      // albiceleste
  "austria": "#EF3340",
  "jordan": "#0B7A3D",
  "colombia": "#FCD116",
  "congo dr": "#008BCE",
  "portugal": "#C8102E",
  "uzbekistan": "#0099B5",
  "croatia": "#D72027",
  "england": "#F2F2F2",
  "ghana": "#006B3F",
  "panama": "#DA121A",
};

function teamColor(canonical) {
  return TEAM_COLORS[canonical] || "#6a9be8";
}
