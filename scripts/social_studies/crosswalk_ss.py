"""Suggested (best-effort) crosswalk: AERO Social Studies K-5 indicator -> Wisconsin SS learning priorities.

Matched by meaning only. The build resolves each learning priority to the WI-SS indicator codes in the same
grade band (AERO x.2.x = K-2, AERO x.5.x = 3-5). Every link is a suggestion for committee review.
"""
AERO_TO_WI = {
    "1.2.a": ["Hist3.a", "Hist2.a"], "1.2.b": ["Hist2.b", "Hist3.c"], "1.2.c": ["Hist3.a", "Hist3.c"],
    "1.5.a": ["Hist3.b", "BH2.b"], "1.5.b": ["Hist2.b", "Hist2.a"], "1.5.c": ["Hist1.a", "Hist1.b"],
    "1.5.d": ["Hist4.a", "Hist4.c", "Inq2.a"],
    "2.2.a": ["BH2.a", "PS4.b"], "2.2.b": ["BH2.a", "PS4.b"], "2.2.c": ["PS4.b", "PS3.d"],
    "2.5.a": ["Econ1.a", "Econ4.d"], "2.5.b": ["Hist1.a", "Hist1.b", "BH2.a"], "2.5.c": ["Econ4.e", "Geog3.b"],
    "3.2.a": ["Geog5.b", "Geog5.a"], "3.2.b": ["Geog1.a", "Geog1.c"], "3.2.c": ["Geog1.b", "Geog1.a"],
    "3.2.d": ["Geog1.b", "Geog4.a"], "3.2.e": ["Geog2.a", "Geog4.a"], "3.2.f": ["BH2.b", "Geog5.a"],
    "3.5.a": ["Geog1.a", "Geog1.c"], "3.5.b": ["Geog1.b", "Geog1.a"], "3.5.c": ["Geog1.a", "Geog1.c"],
    "3.5.d": ["Geog5.a", "Hist2.b"], "3.5.e": ["Geog2.a", "Geog2.b"], "3.5.f": ["Geog2.a", "Geog2.d"],
    "3.5.g": ["Geog4.a", "Geog3.a"], "3.5.h": ["Geog1.c", "Geog4.a"],
    "4.2.a": ["PS1.a", "Hist3.a"], "4.2.b": ["PS3.b", "BH2.a"], "4.2.c": ["BH2.b", "Geog5.b"],
    "4.2.d": ["BH3.a", "BH2.a"], "4.2.e": ["BH3.a", "BH2.b"],
    "4.5.a": ["BH3.a", "Geog4.a"], "4.5.b": ["BH2.a"], "4.5.c": ["BH2.b", "Hist3.b"], "4.5.d": ["Geog4.a", "BH1.b"],
    "4.5.e": ["BH2.b", "BH1.b"], "4.5.f": ["BH2.b", "BH3.a"], "4.5.g": ["BH3.a"], "4.5.h": ["BH3.a", "PS2.c"],
    "4.5.i": ["BH3.a", "Geog3.b"],
    "5.2.a": ["BH1.a", "BH1.b"], "5.2.b": ["BH1.a"], "5.2.c": ["BH2.a"], "5.2.d": ["BH1.b", "PS1.a"],
    "5.2.e": ["BH2.a", "Geog2.a"], "5.2.f": ["BH2.a", "PS2.c"], "5.2.g": ["BH1.b"],
    "5.5.a": ["BH1.a"], "5.5.b": ["BH1.b", "BH1.a"], "5.5.c": ["BH2.a", "BH2.b"], "5.5.d": ["PS3.b", "Econ4.b"],
    "5.5.e": ["BH1.b", "BH2.b"], "5.5.f": ["BH1.b"], "5.5.g": ["BH1.b", "BH2.b"], "5.5.h": ["BH3.a", "PS2.c"],
    "6.2.a": ["PS2.a", "PS2.b"], "6.2.b": ["PS3.c", "PS1.a"], "6.2.c": ["PS2.a", "PS2.b"], "6.2.d": ["PS3.a", "PS1.b"],
    "6.2.e": ["PS3.b", "BH1.a"], "6.2.f": ["PS2.b", "PS2.a"], "6.2.g": ["Inq5.a", "PS2.b"], "6.2.h": ["PS3.d", "PS4.b"],
    "6.2.i": ["PS3.b", "Econ4.b"],
    "6.5.a": ["PS2.a", "PS2.b"], "6.5.b": ["PS3.c", "Econ4.c"], "6.5.c": ["PS3.a", "PS3.c"], "6.5.d": ["PS3.c", "PS1.a"],
    "6.5.e": ["PS3.c"], "6.5.f": ["PS2.b"], "6.5.g": ["PS3.a", "PS2.c", "Inq5.a"], "6.5.h": ["PS1.a", "PS3.c"],
    "6.5.i": ["PS3.c", "PS1.a"], "6.5.j": ["PS4.b", "PS4.a"],
    "7.2.a": ["Econ1.a"], "7.2.b": ["Econ1.a", "Geog5.b"], "7.2.c": ["Econ4.b", "Econ4.e"], "7.2.d": ["Econ2.a", "Econ4.c"],
    "7.2.e": ["Econ1.a", "Econ1.b"], "7.2.f": ["Econ4.b"], "7.2.g": ["Econ2.a", "Econ3.b", "Econ4.e"],
    "7.5.a": ["Geog3.a", "Geog5.b", "Econ1.a"], "7.5.b": ["Econ2.c", "Econ1.a"], "7.5.c": ["Geog3.b"],
    "7.5.d": ["Econ2.c", "Econ2.a"], "7.5.e": ["Econ4.e", "Geog3.b"], "7.5.f": ["Econ4.e", "Hist2.b"], "7.5.g": ["Econ4.e"],
    "8.2.a": ["BH4.a"], "8.2.b": ["BH4.a"], "8.2.c": ["BH4.a"], "8.5.a": ["BH4.a"], "8.5.b": ["BH4.a"],
    "8.5.c": ["BH4.a", "Geog5.a"], "8.5.d": ["BH4.a", "Hist2.b"], "8.5.e": ["BH4.a", "BH2.b"],
}
