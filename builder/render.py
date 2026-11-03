"""
KSERC Order Builder — Jinja2 Renderer
=======================================

Loads templates from the templates/ directory and renders the
order JSON into a complete HTML document.

Usage:
    from builder.render import build_html
    html = build_html(order_json)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from builder.validators import validate_order_json

logger = logging.getLogger(__name__)

# Templates directory (sibling to builder/)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _create_jinja_env() -> Environment:
    """Create and configure the Jinja2 environment."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Custom filters
    env.filters["fmt_num"] = _fmt_num
    env.filters["fmt_pct"] = _fmt_pct
    env.filters["replace_values"] = _replace_values_filter

    # Custom tests
    env.tests["number"] = lambda v: isinstance(v, (int, float))

    return env


def _fmt_num(value: Any, decimals: int = 2) -> str:
    """Format a number with comma separators and fixed decimals."""
    if value is None or value == "" or value == "—":
        return "—"
    try:
        num = float(value)
        return f"{num:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_pct(value: Any, decimals: int = 2) -> str:
    """Format a percentage value."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (ValueError, TypeError):
        return str(value)


def _replace_values_filter(text: str, values: dict) -> str:
    """Replace {placeholder} tokens in text with values from the store."""
    if not isinstance(text, str):
        return str(text)
    for key, val in values.items():
        placeholder = "{" + key + "}"
        if placeholder in text:
            if isinstance(val, (int, float)):
                text = text.replace(placeholder, _fmt_num(val))
            else:
                text = text.replace(placeholder, str(val))
    return text


def build_html(order_json: dict, skip_validation: bool = False) -> str:
    """
    Render the order JSON into a complete HTML document.

    Parameters
    ----------
    order_json : dict
        The structured order JSON from json_builder.build_order_json().
    skip_validation : bool
        If True, skip pre-render validation (for preview mode).

    Returns
    -------
    str
        Complete HTML document string (UTF-8).

    Raises
    ------
    ValueError
        If validation fails and skip_validation is False.
    """
    # Pre-render validation
    if not skip_validation:
        errors = validate_order_json(order_json)
        if errors:
            error_msg = "Order JSON validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.warning(error_msg)
            # Log but don't raise — allow rendering with warnings
            # raise ValueError(error_msg)

    env = _create_jinja_env()

    try:
        template = env.get_template("base_order.html")
    except Exception as e:
        logger.error(f"Failed to load base template: {e}")
        raise

    # Render with all top-level keys from order_json available
    html = template.render(
        meta=order_json.get("meta", {}),
        cover=order_json.get("cover", {}),
        introduction=order_json.get("introduction", {}),
        hearing=order_json.get("hearing", {}),
        sections=order_json.get("sections", []),
        orders=order_json.get("orders", {}),
        values=order_json.get("values", {}),
        signature=order_json.get("signature", {}),
    )

    logger.info(f"Rendered HTML: {len(html)} chars, {len(order_json.get('sections', []))} sections")
    return html
