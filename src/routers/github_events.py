"""GitHub events viewer router."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from logging_config import get_logger
from services.event_store import get_event_store

logger = get_logger(__name__)

router = APIRouter(prefix="/github", tags=["events"])

_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub Events Viewer</title>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont,
      "Segoe UI", Roboto, sans-serif;
    margin: 20px;
    background: #f6f8fa;
    color: #24292f;
  }
  h1 { margin-bottom: 4px; }
  .meta {
    color: #57606a;
    font-size: 14px;
    margin-bottom: 16px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    overflow: hidden;
  }
  th, td {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid #d0d7de;
    font-size: 14px;
  }
  th {
    background: #f6f8fa;
    font-weight: 600;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f6f8fa; }
  .empty {
    text-align: center;
    padding: 40px;
    color: #57606a;
  }
  code {
    background: #f6f8fa;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 12px;
  }
</style>
</head>
<body>
<h1>GitHub Events</h1>
<p class="meta">
  Auto-refreshes every 5 seconds.
  <span id="count"></span>
  <span id="updated"></span>
</p>
<div id="content"><p class="empty">Loading...</p></div>
<script>
async function refresh() {
  try {
    const resp = await fetch("/github/events/api");
    const data = await resp.json();
    const events = data.events;
    const el = document.getElementById("content");
    document.getElementById("count").textContent =
      "Events: " + data.total + ".";
    document.getElementById("updated").textContent =
      "Updated: " + new Date().toLocaleTimeString();
    if (!events.length) {
      el.innerHTML =
        '<p class="empty">No events received yet.</p>';
      return;
    }
    let html = "<table><thead><tr>"
      + "<th>Type</th><th>Action</th><th>Repository</th>"
      + "<th>Sender</th><th>Delivery ID</th>"
      + "<th>Received</th><th>Summary</th>"
      + "</tr></thead><tbody>";
    for (const e of events) {
      const ts = new Date(e.received_at)
        .toLocaleString();
      const summary = JSON.stringify(
        e.payload_summary || {}
      );
      html += "<tr>"
        + "<td><code>" + esc(e.event_type) + "</code></td>"
        + "<td>" + esc(e.action) + "</td>"
        + "<td>" + esc(e.repository) + "</td>"
        + "<td>" + esc(e.sender) + "</td>"
        + "<td><code>"
        + esc((e.delivery_id || "").substring(0, 8))
        + "</code></td>"
        + "<td>" + esc(ts) + "</td>"
        + "<td><code>" + esc(summary) + "</code></td>"
        + "</tr>";
    }
    html += "</tbody></table>";
    el.innerHTML = html;
  } catch (err) {
    console.error("Refresh failed:", err);
  }
}
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


@router.get("/events", response_class=HTMLResponse)
async def events_page() -> HTMLResponse:
    """Serve the GitHub events viewer HTML page.

    Returns:
        HTMLResponse with auto-refreshing events table.
    """
    return HTMLResponse(content=_HTML_PAGE)


@router.get("/events/api")
async def events_api() -> JSONResponse:
    """Return stored events as JSON for the viewer.

    Returns:
        JSONResponse with list of events and total count.
    """
    store = get_event_store()
    events = store.get_all()

    return JSONResponse(
        content={
            "total": store.count,
            "events": [
                e.model_dump(mode="json") for e in events
            ],
        },
    )
