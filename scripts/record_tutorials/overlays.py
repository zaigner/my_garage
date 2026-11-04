"""Cursor, tap-ripple and caption overlays injected into every page."""

from __future__ import annotations

import json

# Hosts the browser may reach: the local app plus the CDNs the templates load.
LOCAL_HOSTS = {"127.0.0.1"}
CDN_ALLOWLIST = {
    "cdn.tailwindcss.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
    "cdnjs.cloudflare.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}


def host_allowed(host: str | None) -> bool:
    return host in LOCAL_HOSTS or host in CDN_ALLOWLIST


INIT_SCRIPT = r"""
(() => {
  const boot = () => {
    const root = document.documentElement;
    if (!root) return false;
    if (document.getElementById('__tut')) return true;
    const style = document.createElement('style');
    style.id = '__tut';
    style.textContent = `
      [data-tutorial-video] { display: none !important; }
      #__tut_cursor { position: fixed; z-index: 2147483647; left: 0; top: 0;
        width: 26px; height: 26px; margin: -13px 0 0 -13px; border-radius: 50%;
        background: rgba(255,255,255,.85); border: 3px solid #D4AF37;
        box-shadow: 0 2px 8px rgba(0,0,0,.6); pointer-events: none; }
      .__tut_ripple { position: fixed; z-index: 2147483646; width: 24px; height: 24px;
        margin: -12px 0 0 -12px; border-radius: 50%; border: 3px solid #D4AF37;
        background: rgba(212,175,55,.35); pointer-events: none;
        animation: __tut_rip .6s ease-out forwards; }
      @keyframes __tut_rip { from { transform: scale(.4); opacity: 1; }
                             to { transform: scale(3); opacity: 0; } }
      #__tut_caption { position: fixed; z-index: 2147483645; left: 50%; bottom: 36px;
        transform: translateX(-50%); width: 350px; box-sizing: border-box;
        padding: 14px 18px; text-align: center; pointer-events: none;
        font: italic 600 21px/1.3 'Playfair Display', Georgia, serif;
        color: #D4AF37; background: rgba(11,16,38,.94);
        border: 1px solid rgba(212,175,55,.5); border-radius: 6px; display: none; }
    `;
    root.appendChild(style);
    const cursor = document.createElement('div');
    cursor.id = '__tut_cursor';
    root.appendChild(cursor);
    const caption = document.createElement('div');
    caption.id = '__tut_caption';
    root.appendChild(caption);
    let xy = __CURSOR_XY__;
    try { xy = JSON.parse(sessionStorage.getItem('__tut_xy')) || xy; } catch (e) {}
    const place = (x, y) => {
      cursor.style.transform = `translate(${x}px, ${y}px)`;
      try { sessionStorage.setItem('__tut_xy', JSON.stringify([x, y])); } catch (e) {}
    };
    place(xy[0], xy[1]);
    document.addEventListener('mousemove', e => place(e.clientX, e.clientY), true);
    document.addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.className = '__tut_ripple';
      r.style.left = e.clientX + 'px';
      r.style.top = e.clientY + 'px';
      root.appendChild(r);
      setTimeout(() => r.remove(), 700);
    }, true);
    window.__tutCaption = text => {
      caption.textContent = text;
      caption.style.display = text ? 'block' : 'none';
    };
    return true;
  };
  if (!boot()) {
    const mo = new MutationObserver(() => { if (boot()) mo.disconnect(); });
    mo.observe(document, { childList: true });
  }
})();
"""


def init_script(variant) -> str:
    return INIT_SCRIPT.replace("__CURSOR_XY__", json.dumps(list(variant.cursor_start)))


def install(context, variant) -> None:
    """Add the overlays to every page the context opens."""
    context.add_init_script(init_script(variant))


def caption(rec, text: str, hold_ms: int) -> None:
    """Show ``text`` as an on-screen caption, then wait a fixed time."""
    rec.log(f"caption: {text}")
    rec.page.evaluate("t => window.__tutCaption(t)", text)
    rec.page.wait_for_timeout(hold_ms)


def glide(rec, x: float, y: float, ms: int = 700) -> None:
    """Move the mouse in small timed steps so the cursor visibly travels."""
    steps = max(1, ms // 20)
    x0, y0 = rec.mouse_xy
    for i in range(1, steps + 1):
        t = i / steps
        t = t * t * (3 - 2 * t)  # smoothstep
        rec.page.mouse.move(x0 + (x - x0) * t, y0 + (y - y0) * t)
        rec.page.wait_for_timeout(20)
    rec.mouse_xy = (x, y)


def tap(rec, locator, glide_ms: int = 700, settle_ms: int = 350) -> None:
    """Bring ``locator`` into view, glide the cursor to it and tap."""
    locator.wait_for(state="visible")
    # Centre it (instantly, whatever scroll-behavior the page sets) so it clears
    # both the nav and the caption bar, then wait until it stops moving.
    locator.evaluate("el => el.scrollIntoView({block: 'center', behavior: 'instant'})")
    box = None
    for _ in range(20):
        rec.page.wait_for_timeout(150)
        latest = locator.bounding_box()
        if latest is not None and latest == box:
            break
        box = latest
    else:
        raise RuntimeError("element never stopped moving")
    if box is None:
        raise RuntimeError("element has no bounding box")
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    glide(rec, x, y, glide_ms)
    rec.page.wait_for_timeout(settle_ms)
    rec.page.mouse.down()
    rec.page.wait_for_timeout(90)
    rec.page.mouse.up()
