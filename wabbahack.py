import argparse
import os
import tkinter as tk
import numpy as np
import cv2
import pyautogui
from PIL import Image

# --------------------
# Config
# --------------------
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
pyautogui.FAILSAFE = True
warn = 'warn.png'
buttons = ('standard.png', 'slow.png', warn)
confidence = 0.9
poll_interval = 1
# Browser zoom steps (relative to the zoom the templates were captured at).
# Template matching tolerates only a few percent of size error, so these are
# discrete zoom levels rather than an arbitrary sweep. Trim to what you use;
# each entry adds one match per button per scan.
scales = (1.0, 1.1, 0.9, 1.25, 0.8, 1.5, 0.75)

DEBUG = False

# --------------------
# Helpers
# --------------------
def log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")


def to_gray(img):
    """PIL RGB image -> 2D uint8 grayscale numpy array."""
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)


def build_templates(base_images, scales):
    """Resize each (name, PIL image) at every scale, as grayscale arrays.

    Scales closest to 1.0 come first, so find_button (first match wins) tries
    the most likely sizes first. Several entries share each button's name.
    """
    ordered = sorted(scales, key=lambda s: abs(s - 1.0))
    templates = []
    for name, base in base_images:
        base = base.convert("L")
        w, h = base.size
        for s in ordered:
            size = (max(1, round(w * s)), max(1, round(h * s)))
            templates.append((name, np.array(base.resize(size, Image.LANCZOS))))
    return templates


def find_button(gray_haystack, region_x, region_y, loaded_buttons, conf=0.9):
    """Search a grayscale numpy array for any pre-converted needle.

    Args:
        gray_haystack: 2D uint8 numpy array (grayscale screenshot)
        region_x, region_y: absolute screen offset of the haystack
        loaded_buttons: list of (name, gray_numpy_array) tuples
        conf: match confidence threshold

    Returns:
        (Point, name) if found, (None, None) if not
    """
    hh, hw = gray_haystack.shape[:2]

    for name, needle in loaded_buttons:
        nh, nw = needle.shape[:2]
        if nw > hw or nh > hh:
            continue  # needle larger than haystack - skip

        result = cv2.matchTemplate(gray_haystack, needle, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= conf:
            cx = region_x + max_loc[0] + nw // 2
            cy = region_y + max_loc[1] + nh // 2
            return pyautogui.Point(cx, cy), name

    return None, None


# --------------------
# Main
# --------------------
def main():
    global DEBUG

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--region", type=str, default=None,
        help="Fixed search region as x,y,w,h (e.g. '0,0,1920,1080'). "
             "Defaults to full screen."
    )
    args = parser.parse_args()
    DEBUG = args.debug

    # Load button images at multiple scales, pre-converted to grayscale numpy.
    base_images = []
    for filename in buttons:
        full_path = os.path.join(ASSETS_DIR, filename)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Button image not found: {full_path}")
        base_images.append((filename, Image.open(full_path).convert("RGB")))
    loaded_buttons = build_templates(base_images, scales)

    # Search region - full screen by default, or a fixed tuple via --region.
    if args.region:
        parts = args.region.split(",")
        if len(parts) != 4:
            parser.error("--region must be x,y,w,h (four comma-separated integers)")
        try:
            region = tuple(int(p.strip()) for p in parts)
        except ValueError:
            parser.error(f"--region values must be integers, got '{args.region}'")
    else:
        w, h = pyautogui.size()
        region = (0, 0, w, h)

    # Tiny status window.
    root = tk.Tk()
    screen_w = root.winfo_screenwidth()
    win_w, win_h = 280, 84

    root.title("Wabbahack")
    root.geometry(f"{win_w}x{win_h}+{screen_w - win_w - 16}+{16}")

    status_var = tk.StringVar(value="Running…")
    status_label = tk.Label(root, textvariable=status_var)
    status_label.pack(expand=True)

    stop_btn = tk.Button(root, text="Stop", command=root.destroy)
    stop_btn.pack(pady=(0, 8))

    def stop_button_center():
        """Absolute screen coords of the Stop button's centre."""
        return pyautogui.Point(
            stop_btn.winfo_rootx() + stop_btn.winfo_width() // 2,
            stop_btn.winfo_rooty() + stop_btn.winfo_height() // 2,
        )

    # Frame-diff state: small downsampled grayscale for cheap change detection.
    prev_small = None

    def tick():
        nonlocal prev_small

        try:
            # Explicit emergency-stop check
            if pyautogui.position() in pyautogui.FAILSAFE_POINTS:
                raise pyautogui.FailSafeException
            
            screenshot = pyautogui.screenshot(region=region)

            # Convert to grayscale numpy once per cycle.
            gray_haystack = to_gray(screenshot)

            # Cheap change detection: compare a tiny downsampled version.
            # INTER_AREA averages source pixels, so small changes aren't
            # skipped over the way default INTER_LINEAR sampling can.
            small = cv2.resize(gray_haystack, (64, 36), interpolation=cv2.INTER_AREA)
            if prev_small is not None and np.array_equal(small, prev_small):
                # Screen unchanged - skip expensive matching entirely.
                status_var.set("Running…")
            else:
                prev_small = small
                region_x, region_y, _, _ = region
                location, button = find_button(
                    gray_haystack, region_x, region_y, loaded_buttons, confidence
                )

                if location:
                    status_var.set(f"Found {button}")
                    log(f"Found button: {button}")
                    if button == warn:
                        pyautogui.moveTo(location)
                        pyautogui.scroll(-500)
                    else:
                        pyautogui.click(location)
                        # Park the mouse over the Stop button between clicks so
                        # it's easy to grab and abort quickly.
                        pyautogui.moveTo(stop_button_center(), duration=0.2)
                    # Force a fresh scan next tick: if the click/scroll didn't
                    # change the screen, an identical frame would otherwise be
                    # skipped and the action never retried.
                    prev_small = None
                else:
                    status_var.set("Running…")

        except pyautogui.FailSafeException:
            # Failsafe corner hit - stop polling and close the window.
            root.destroy()
            return
        except Exception as e:
            log(f"Error this iteration: {e!r}")
            status_var.set("Error (retrying)…")

        root.after(int(poll_interval * 1000), tick)

    print("Starting Wabbahack. Click Stop to quit.")
    root.after(200, tick)
    root.mainloop()

    print("\nStopping.")


if __name__ == "__main__":
    main()