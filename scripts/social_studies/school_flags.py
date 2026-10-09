"""Committee-review flags on the school's K-5 report-card sheet (checked by hand against the AERO PDF)."""

# (grade, code) -> note.  'W' = school wording differs from the official AERO indicator for that code;
# 'D' = school descriptors do not match the standard on the same row; 'P' = school grade differs from AERO placement.
FLAGS = {
    ("K", "1.2.a"): "D: descriptors describe comparing cultures (food, clothes, holidays), not stories about the past.",
    ("K", "6.2.a"): "W: school wording 'role of individuals in a community' differs from official 6.2.a (rights and responsibilities, good citizens).",
    ("K", "6.2.b"): "W: school wording 'individuals have unique roles' differs from official 6.2.b (sources and purposes of authority).",
    ("K", "7.2.a"): "W: school wording 'how communities and cultures are connected' differs from official 7.2.a (needs and wants).",
    ("K", "8.2.a"): "W: school wording 'role of technology in society' differs from official 8.2.a (tool vs technique).",
    ("1", "3.2.b"): "P: AERO places 3.2.b in Grade 2 (school also lists it in Grade 2).",
    ("1", "5.2.b"): "P: AERO places 5.2.b in K. W: school adds 'recognize group behavior'.",
    ("1", "6.2.b"): "P: AERO places 6.2.b in K.",
    ("2", "1.2.c"): "D: descriptors are about local places and their purposes.",
    ("2", "2.2.c"): "D: descriptors are about Qatari cultural symbols.",
    ("2", "3.2.b"): "D: descriptors are about traditional Qatari foods.",
    ("2", "3.2.c"): "D: descriptors are about Qatari traditions.",
    ("2", "3.2.d"): "D: descriptors are about Qatari art.",
    ("2", "3.2.e"): "D: descriptors are about Qatari festivals.",
    ("2", "3.2.f"): "D: descriptors are about Qatari leaders.",
    ("2", "4.2.c"): "P: AERO places 4.2.c in Grade 1. No school descriptors (draft used).",
    ("3", "3.5.a"): "W: school wording (influence of landforms) matches AERO 3.2.e, not 3.5.a (elements of maps and globes).",
    ("3", "4.5.a"): "W: school wording (social environments in different cultures) is closer to AERO 4.2.d.",
    ("3", "5.5.a"): "W: school wording (why people live in social groups) matches AERO 5.2.e, not 5.5.a (families influence the individual).",
    ("3", "6.5.a"): "W: school wording (importance of leadership and service) matches AERO 6.2.g, not 6.5.a.",
    ("4", "1.5.b"): "W: school wording combines AERO 1.5.a (Grade 3) and 1.5.b.",
    ("4", "2.5.b"): "W: school wording (wants and needs beyond the self) matches AERO 2.5.a (Grade 3), not 2.5.b.",
    ("5", "1.5.c"): "P: AERO places 1.5.c in Grade 4. W: school wording also includes 1.5.d (primary and secondary sources).",
    ("5", "2.5.c"): "W: school wording combines AERO 2.5.b (Grade 4) and 2.5.c.",
    ("5", "3.5.c"): "P: AERO places 3.5.c in Grade 4. W: school wording also includes 3.5.f (settlement and land use).",
    ("5", "4.5.c"): "P/W/D: AERO 4.5.c is folktales (Grade 3); school wording matches 4.5.i + 4.5.f; descriptors are about family and cultural identity.",
    ("5", "6.5.c"): "P/W: AERO 6.5.c is community leaders (Grade 3); school wording matches 6.5.d/6.5.i + 6.5.h.",
    ("5", "7.5.c"): "P/W: AERO 7.5.c is transport and trade (Grade 4); school wording matches 7.5.g + 7.5.f.",
    ("5", "8.5.c"): "P/W: AERO 8.5.c is positive and negative effects (Grade 3); school wording matches 8.5.e.",
}

MASTER_DIFFS = [('3.2.a', 'K', '1'), ('3.2.b', 'K', '2'), ('6.2.c', 'K', '1'), ('7.2.b', 'K', '1'), ('3.2.c', '1', '2'),
                ('3.2.d', '1', '2'), ('5.2.c', '1', 'K'), ('6.2.f', '1', '2'), ('4.2.c', '2', '1'), ('5.2.e', '2', '1'),
                ('6.5.d', '3', '4'), ('3.5.e', '4', '5'), ('4.5.e', '4', '5'), ('4.5.f', '4', '5'), ('5.5.c', '4', '3'),
                ('5.5.d', '4', '3'), ('8.5.b', '4', '3'), ('8.5.c', '4', '3'), ('1.5.c', '5', '4'), ('5.5.e', '5', '4'),
                ('6.5.h', '5', '4'), ('8.5.d', '5', '4')]
