"""Static 2026 World Cup knockout bracket (the official FIFA structure).

48 teams -> 12 group winners + 12 runners-up + the 8 best third-placed teams fill
the 32-team knockout. Slot names:
  W_<G>   group winner of group G          RU_<G>  runner-up of group G
  T<m>    a best-third-place team feeding Round-of-32 match m (eligibility below)

Source: 2026 FIFA World Cup knockout stage (match numbers 73-104).
"""
from __future__ import annotations

# Round of 32: match number -> (home slot, away slot)
R32_MATCHES = {
    73: ("RU_A", "RU_B"),
    74: ("W_E", "T74"),
    75: ("W_F", "RU_C"),
    76: ("W_C", "RU_F"),
    77: ("W_I", "T77"),
    78: ("RU_E", "RU_I"),
    79: ("W_A", "T79"),
    80: ("W_L", "T80"),
    81: ("W_D", "T81"),
    82: ("W_G", "T82"),
    83: ("RU_K", "RU_L"),
    84: ("W_H", "RU_J"),
    85: ("W_B", "T85"),
    86: ("W_J", "RU_H"),
    87: ("W_K", "T87"),
    88: ("RU_D", "RU_G"),
}

# Each third-place slot may only be filled by a third from one of these groups.
THIRD_SLOT_ELIGIBILITY = {
    "T74": set("ABCDF"),
    "T77": set("CDFGH"),
    "T79": set("CEFHI"),
    "T80": set("EHIJK"),
    "T81": set("BEFIJ"),
    "T82": set("AEHIJ"),
    "T85": set("EFGIJ"),
    "T87": set("DEIJL"),
}

# Later rounds: match number -> (feeder match A, feeder match B)
KO_TREE = {
    # Round of 16
    89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
    93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
    # Quarter-finals
    97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96),
    # Semi-finals
    101: (97, 98), 102: (99, 100),
    # Final
    104: (101, 102),
}

# The stage a team REACHES by winning a given match.
STAGE_REACHED_BY_WINNING = {
    **{m: "R16" for m in R32_MATCHES},
    **{m: "QF" for m in (89, 90, 91, 92, 93, 94, 95, 96)},
    **{m: "SF" for m in (97, 98, 99, 100)},
    **{m: "FINAL" for m in (101, 102)},
    104: "WINNER",
}

STAGES = ["R32", "R16", "QF", "SF", "FINAL", "WINNER"]
