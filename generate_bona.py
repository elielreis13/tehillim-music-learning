"""
Generator for Bona Method lessons 1-8 (page 7: Primeira Parte)
Exercises in C major, 4/4 time, treble clef.

Lesson overview:
  1 - Escalas de Semibreves (whole notes) ascending + descending
  2 - A mesma em Mínimas (half notes)
  3 - Em Semínimas (quarter notes)
  4 - Em Colcheias (eighth notes)
  5 - Em Semicolcheias (sixteenth notes)
  6 - Em saltos de Terça, Mínimas (thirds + half notes)
  7 - Em saltos de Terça, Semínimas (thirds + quarter notes)
  8 - Em saltos de Terça, Colcheias (thirds + eighth notes)
"""

import os

OUTPUT_DIR = "/Users/insider/Documents/Projects/tehillim-music-learning/tehillim/static/bona"

HEADER = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>{title}</work-title>
  </work>
  <identification>
    <encoding>
      <software>Plataforma Tehillim</software>
    </encoding>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Melodia</part-name>
    </score-part>
  </part-list>
  <part id="P1">
'''

FOOTER = '''  </part>
</score-partwise>
'''

# C major scale: C4 to C5 ascending, then C5 to C4 descending
SCALE_UP   = [("C",4),("D",4),("E",4),("F",4),("G",4),("A",4),("B",4),("C",5)]
SCALE_DOWN = [("C",5),("B",4),("A",4),("G",4),("F",4),("E",4),("D",4),("C",4)]

# Scale in thirds (ascending then descending)
THIRDS_UP   = [("C",4),("E",4),("D",4),("F",4),("E",4),("G",4),
               ("F",4),("A",4),("G",4),("B",4),("A",4),("C",5)]
THIRDS_DOWN = [("C",5),("A",4),("B",4),("G",4),("A",4),("F",4),
               ("G",4),("E",4),("F",4),("D",4),("E",4),("C",4)]

DURATION_MAP = {
    "whole":    (16, "whole"),
    "half":     (8,  "half"),
    "quarter":  (4,  "quarter"),
    "eighth":   (2,  "eighth"),
    "16th":     (1,  "16th"),
}

def note_xml(step, octave, duration_name, is_last=False, beam_state=None):
    dur, typ = DURATION_MAP[duration_name]
    lines = []
    lines.append("      <note>")
    lines.append(f"        <pitch><step>{step}</step><octave>{octave}</octave></pitch>")
    lines.append(f"        <duration>{dur}</duration>")
    lines.append(f"        <type>{typ}</type>")
    # Add beams for eighth/16th notes
    if beam_state and duration_name in ("eighth", "16th"):
        if duration_name == "16th":
            b1, b2 = beam_state
            if b1:
                lines.append(f'        <beam number="1">{b1}</beam>')
            if b2:
                lines.append(f'        <beam number="2">{b2}</beam>')
        else:
            if beam_state:
                lines.append(f'        <beam number="1">{beam_state}</beam>')
    if is_last:
        lines.append("        <notations><fermata/></notations>")
    lines.append("      </note>")
    return "\n".join(lines)

def measure_xml(number, notes_xml, is_first=False):
    lines = []
    lines.append(f'    <measure number="{number}">')
    if is_first:
        lines.append("      <attributes>")
        lines.append("        <divisions>4</divisions>")
        lines.append("        <key><fifths>0</fifths><mode>major</mode></key>")
        lines.append("        <time><beats>4</beats><beat-type>4</beat-type></time>")
        lines.append("        <clef><sign>G</sign><line>2</line></clef>")
        lines.append("      </attributes>")
    lines.append(notes_xml)
    lines.append("    </measure>")
    return "\n".join(lines)

def build_measures_from_notes(notes, dur_name, notes_per_measure):
    """
    Group a flat list of (step, octave) tuples into measures.
    Returns list of measure content strings.
    """
    measures = []
    total = len(notes)
    idx = 0
    m_num = 1

    while idx < total:
        chunk = notes[idx:idx+notes_per_measure]
        note_lines = []
        for i, (step, octave) in enumerate(chunk):
            is_last = (idx + i == total - 1)
            beam_state = compute_beam(i, len(chunk), dur_name, notes_per_measure)
            note_lines.append(note_xml(step, octave, dur_name, is_last=is_last, beam_state=beam_state))
        content = "\n".join(note_lines)
        measures.append(measure_xml(m_num, content, is_first=(m_num == 1)))
        idx += notes_per_measure
        m_num += 1

    return measures


def compute_beam(pos_in_measure, chunk_size, dur_name, notes_per_measure):
    """Simple beam logic: beam groups of 4 eighth notes, groups of 4 for 16th."""
    if dur_name == "eighth":
        group = pos_in_measure % 4
        if group == 0:
            return "begin" if chunk_size - pos_in_measure > 1 else None
        elif group == 3 or pos_in_measure == chunk_size - 1:
            return "end"
        else:
            return "continue"
    elif dur_name == "16th":
        # Group 4 sixteenth notes per beam group
        group = pos_in_measure % 4
        if group == 0:
            b1 = "begin"
            b2 = "begin"
        elif group == 3 or pos_in_measure == chunk_size - 1:
            b1 = "end"
            b2 = "end"
        else:
            b1 = "continue"
            b2 = "continue"
        return (b1, b2)
    return None


def build_score(title, notes, dur_name, notes_per_measure):
    measures = build_measures_from_notes(notes, dur_name, notes_per_measure)
    body = "\n".join(measures)
    return HEADER.format(title=title) + body + "\n" + FOOTER


# ── Notes per measure by duration type ──────────────────────────────────────
NOTES_PER_MEASURE = {
    "whole":   1,
    "half":    2,
    "quarter": 4,
    "eighth":  8,
    "16th":    16,
}

# ── Exercise definitions ─────────────────────────────────────────────────────
EXERCISES = [
    # (lesson_num, title, notes, dur_name)
    (1, "Método Bona - Lição 1: Escalas de Semibreves",
     SCALE_UP + SCALE_DOWN, "whole"),

    (2, "Método Bona - Lição 2: Escalas em Mínimas",
     SCALE_UP + SCALE_DOWN, "half"),

    (3, "Método Bona - Lição 3: Em Semínimas",
     SCALE_UP + SCALE_DOWN, "quarter"),

    (4, "Método Bona - Lição 4: Em Colcheias",
     SCALE_UP + SCALE_DOWN, "eighth"),

    (5, "Método Bona - Lição 5: Em Semicolcheias",
     # ascending + descending including C5 at both ends of turn = 16 notes (1 measure)
     SCALE_UP + SCALE_DOWN, "16th"),

    (6, "Método Bona - Lição 6: Em Saltos de Terça (Mínimas)",
     THIRDS_UP + THIRDS_DOWN, "half"),

    (7, "Método Bona - Lição 7: Em Saltos de Terça (Semínimas)",
     THIRDS_UP + THIRDS_DOWN, "quarter"),

    (8, "Método Bona - Lição 8: Em Saltos de Terça (Colcheias)",
     THIRDS_UP + THIRDS_DOWN, "eighth"),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for lesson_num, title, notes, dur_name in EXERCISES:
        npm = NOTES_PER_MEASURE[dur_name]
        xml = build_score(title, notes, dur_name, npm)
        path = os.path.join(OUTPUT_DIR, f"bona-licao-{lesson_num}.musicxml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"Created: {path} ({len(notes)} notes, {dur_name}, {len(notes)//npm} measures)")


if __name__ == "__main__":
    main()
