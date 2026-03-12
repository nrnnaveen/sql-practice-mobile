"""Visualizer service – produces animation metadata for a given query type."""
from app.services.query_parser_service import (
    SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, OTHER
)


# ---------------------------------------------------------------------------
# Animation step templates
# ---------------------------------------------------------------------------

_SELECT_STEPS = [
    {"delay": 0,    "action": "highlight_table",   "target": "table-box",    "style": {"boxShadow": "0 0 30px #2196F3", "borderColor": "#2196F3"}},
    {"delay": 500,  "action": "highlight_columns",  "target": "table-header", "style": {"background": "#FFEB3B33"}},
    {"delay": 1000, "action": "slide_rows",          "target": "table-rows",   "style": {"y": "-200px", "opacity": 1}},
    {"delay": 1500, "action": "show_results",        "target": "result-panel", "style": {"opacity": 1}},
    {"delay": 2500, "action": "fade_highlight",      "target": "table-box",    "style": {"boxShadow": "none"}},
]

_INSERT_STEPS = [
    {"delay": 0,    "action": "highlight_table",  "target": "table-box",  "style": {"boxShadow": "0 0 30px #4CAF50", "borderColor": "#4CAF50"}},
    {"delay": 500,  "action": "show_new_row",      "target": "new-row",    "style": {"y": -50, "opacity": 0}},
    {"delay": 1000, "action": "slide_row_in",      "target": "new-row",    "style": {"y": 0, "opacity": 1, "ease": "back.out(1.7)"}},
    {"delay": 2000, "action": "highlight_new_row", "target": "new-row",    "style": {"background": "#FFEB3B"}},
    {"delay": 3000, "action": "fade_highlight",    "target": "new-row",    "style": {"background": "transparent"}},
]

_UPDATE_STEPS = [
    {"delay": 0,    "action": "highlight_row",      "target": "affected-row",  "style": {"background": "#FF980033"}},
    {"delay": 1000, "action": "highlight_cell",     "target": "affected-cell", "style": {"scale": 1.1, "background": "#F4433633"}},
    {"delay": 1500, "action": "fade_old_value",     "target": "old-value",     "style": {"opacity": 0}},
    {"delay": 2000, "action": "show_new_value",     "target": "new-value",     "style": {"opacity": 1}},
    {"delay": 3000, "action": "fade_highlight",     "target": "affected-row",  "style": {"background": "transparent"}},
]

_DELETE_STEPS = [
    {"delay": 0,    "action": "highlight_row",    "target": "deleted-row", "style": {"borderColor": "#F44336"}},
    {"delay": 1000, "action": "redden_row",        "target": "deleted-row", "style": {"background": "rgba(244,67,54,0.3)"}},
    {"delay": 2000, "action": "fade_row",          "target": "deleted-row", "style": {"opacity": 0}},
    {"delay": 3000, "action": "slide_away",        "target": "deleted-row", "style": {"x": 500, "opacity": 0}},
]

_CREATE_STEPS = [
    {"delay": 0,    "action": "show_table",        "target": "new-table",    "style": {"scale": 0, "transformOrigin": "center"}},
    {"delay": 500,  "action": "scale_table",       "target": "new-table",    "style": {"scale": 1}},
    {"delay": 1000, "action": "show_header",       "target": "table-header", "style": {"y": -20, "opacity": 0}},
    {"delay": 1500, "action": "slide_columns",     "target": "table-column", "style": {"x": -100, "opacity": 0, "stagger": 0.3}},
    {"delay": 3000, "action": "add_shadow",        "target": "new-table",    "style": {"boxShadow": "0 8px 30px rgba(0,0,0,0.4)"}},
]

_ALTER_STEPS = [
    {"delay": 0,    "action": "highlight_table", "target": "table-box",    "style": {"boxShadow": "0 0 30px #9C27B0", "borderColor": "#9C27B0"}},
    {"delay": 1000, "action": "pulse_table",     "target": "table-box",    "style": {"scale": 1.02}},
    {"delay": 2000, "action": "reset_table",     "target": "table-box",    "style": {"scale": 1}},
    {"delay": 2500, "action": "fade_highlight",  "target": "table-box",    "style": {"boxShadow": "none"}},
]

_DEFAULT_STEPS = [
    {"delay": 0,   "action": "pulse_table", "target": "table-box", "style": {"boxShadow": "0 0 20px #607D8B"}},
    {"delay": 1500, "action": "fade_highlight", "target": "table-box", "style": {"boxShadow": "none"}},
]

_STEPS_MAP = {
    SELECT: _SELECT_STEPS,
    INSERT: _INSERT_STEPS,
    UPDATE: _UPDATE_STEPS,
    DELETE: _DELETE_STEPS,
    CREATE: _CREATE_STEPS,
    ALTER:  _ALTER_STEPS,
    DROP:   _ALTER_STEPS,   # reuse ALTER animation
    OTHER:  _DEFAULT_STEPS,
}

_DURATION_MAP = {
    SELECT: 3000,
    INSERT: 3500,
    UPDATE: 3500,
    DELETE: 3500,
    CREATE: 3500,
    ALTER:  3000,
    DROP:   3000,
    OTHER:  2000,
}

_COLOR_MAP = {
    SELECT: "#2196F3",
    INSERT: "#4CAF50",
    UPDATE: "#FF9800",
    DELETE: "#F44336",
    CREATE: "#9C27B0",
    ALTER:  "#9C27B0",
    DROP:   "#F44336",
    OTHER:  "#607D8B",
}

_DESCRIPTION_MAP = {
    SELECT: "Rows are being selected from the table",
    INSERT: "A new row is being inserted into the table",
    UPDATE: "Existing row values are being updated",
    DELETE: "Matching rows are being removed from the table",
    CREATE: "A new table structure is being created",
    ALTER:  "The table structure is being modified",
    DROP:   "The table is being dropped",
    OTHER:  "Query is executing",
}


def get_animation_data(query_type: str) -> dict:
    """Return a complete animation descriptor for *query_type*.

    The descriptor is JSON-serialisable and is consumed by the frontend
    ``visualizer_engine.js``.
    """
    steps = _STEPS_MAP.get(query_type, _DEFAULT_STEPS)
    return {
        "query_type":  query_type,
        "color":       _COLOR_MAP.get(query_type, "#607D8B"),
        "duration_ms": _DURATION_MAP.get(query_type, 2000),
        "description": _DESCRIPTION_MAP.get(query_type, "Executing query"),
        "steps":       steps,
    }
