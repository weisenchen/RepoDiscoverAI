from fastapi.templating import Jinja2Templates
from datetime import datetime
import os

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

def format_number(n):
    """Format large numbers with k/M suffixes."""
    if n is None:
        return "0"
    if n >= 1000000:
        return f"{n/1000000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def time_ago(dt_str):
    """Format datetime string as human-readable 'ago' text."""
    if not dt_str:
        return "recently"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        
        if diff.days > 365:
            return f"{diff.days // 365}y ago"
        if diff.days > 30:
            return f"{diff.days // 30}mo ago"
        if diff.days > 0:
            return f"{diff.days}d ago"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        if diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "just now"
    except Exception:
        return dt_str

# Register filters
templates.env.filters["format_number"] = format_number
templates.env.filters["time_ago"] = time_ago

def is_htmx(request):
    """Check if the request is an HTMX request."""
    return request.headers.get("HX-Request") == "true"
