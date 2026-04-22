"""Pre-compiled TikTok Studio actions. Import from domain skill scripts:
    from tiktok.actions import upload_video, set_caption, dismiss_stale_drafts
"""
import json, time
from helpers import (
    cdp, click, goto, js, new_tab, page_info, press_key, screenshot,
    scroll, type_text, upload_file, verify, wait, wait_for_load,
)

STUDIO_UPLOAD = "https://www.tiktok.com/tiktokstudio/upload?from=upload&lang=en"
CAPTION_SEL = 'div[contenteditable="true"][role="combobox"]'


def dismiss_stale_drafts(max_attempts=3):
    """Dismiss 'A video you were editing wasn't saved' banners. Returns count dismissed."""
    dismissed = 0
    for _ in range(max_attempts):
        banner = js(
            "JSON.stringify(Array.from(document.querySelectorAll('button')).filter("
            "b=>b.textContent.trim()==='Discard').map(b=>{var r=b.getBoundingClientRect();"
            "return {x:r.x+r.width/2,y:r.y+r.height/2}}))"
        )
        buttons = json.loads(banner or "[]")
        if not buttons:
            break
        # Click the banner Discard (y < 300)
        for b in buttons:
            if b["y"] < 300:
                click(int(b["x"]), int(b["y"]))
                time.sleep(1)
                break
        # Click the modal confirm Discard (y > 300)
        banner2 = js(
            "JSON.stringify(Array.from(document.querySelectorAll('button')).filter("
            "b=>b.textContent.trim()==='Discard'&&b.getBoundingClientRect().y>300).map("
            "b=>{var r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}}))"
        )
        confirms = json.loads(banner2 or "[]")
        if confirms:
            click(int(confirms[0]["x"]), int(confirms[0]["y"]))
            time.sleep(1)
            dismissed += 1
    return dismissed


def set_caption(text):
    """Clear existing caption and type new text. Returns the caption as read back."""
    js(f"document.querySelector('{CAPTION_SEL}').focus()")
    press_key("End")
    for _ in range(50):
        press_key("Backspace")
    type_text(text)
    press_key("Escape")  # dismiss hashtag suggestions
    click(700, 50)        # click away to deselect
    time.sleep(0.5)
    return js(f"document.querySelector('{CAPTION_SEL}').innerText")


def attach_video(file_path, processing_wait=12):
    """Upload file and wait for processing. Returns True if file input accepted."""
    upload_file('input[type="file"]', file_path)
    time.sleep(processing_wait)
    return True


def click_schedule_radio():
    """Select the Schedule radio button instead of Post Now."""
    js(
        "(()=>{var l=document.querySelectorAll('label');"
        "for(var i=0;i<l.length;i++){if(l[i].textContent.trim()==='Schedule'){"
        "l[i].click();break}}})()"
    )
    time.sleep(0.5)


def upload_video(file_path, caption, schedule=False):
    """Complete upload flow: navigate → dismiss drafts → attach → caption → submit.

    Returns dict with success status and final URL. Does NOT handle scheduling
    time selection (too dependent on visual coordinates) — call click_schedule_radio()
    and handle the time picker manually if schedule=True.

    For irreversible actions (final submit), this function prints the state and
    returns without clicking — the agent must confirm with the user first.
    """
    new_tab(STUDIO_UPLOAD)
    wait_for_load()
    time.sleep(2)

    # Dismiss any stale draft banners
    dismissed = dismiss_stale_drafts()
    if dismissed:
        print(f"Dismissed {dismissed} stale draft(s)")

    # Attach video
    attach_video(file_path)

    # Set caption
    actual_caption = set_caption(caption)
    print(f"Caption set: {actual_caption}")

    # Schedule mode if requested
    if schedule:
        click_schedule_radio()
        print("Schedule radio selected — set time manually via time picker")

    # Verify state before submit (don't auto-submit — irreversible)
    info = page_info()
    screenshot()
    print(json.dumps({
        "status": "READY_TO_SUBMIT",
        "url": info.get("url"),
        "caption": actual_caption,
        "schedule_mode": schedule,
        "screenshot": "/tmp/shot.png",
        "next": "Review screenshot. If correct, click the Post/Schedule button."
    }, indent=2))
    return {"ready": True, "caption": actual_caption}
