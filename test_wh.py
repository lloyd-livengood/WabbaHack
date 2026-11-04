"""
Test suite for wabbahack.py - verifies button matching logic.
Uses real button images (standard.png, slow.png, warn.png) and a composite
test image (image_test.png) containing all three buttons.

Run with: pytest test_wh.py -v
"""

import os
import pytest
from PIL import Image
from wabbahack import find_button, to_gray, build_templates, scales


# --------------------
# Fixtures
# --------------------

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def load_image(name):
    return Image.open(os.path.join(ASSETS_DIR, name)).convert("RGB")


@pytest.fixture(scope="module")
def standard_img():
    return load_image("standard.png")


@pytest.fixture(scope="module")
def slow_img():
    return load_image("slow.png")


@pytest.fixture(scope="module")
def warn_img():
    return load_image("warn.png")


@pytest.fixture(scope="module")
def composite():
    """Full composite image with all three buttons visible. Size: 1265x369."""
    return load_image("image_test.png")


@pytest.fixture(scope="module")
def clean_strip(composite):
    """Top strip of the composite with no buttons. Size: 1265x100."""
    return composite.crop((0, 0, 1265, 100))


def native(*named_images):
    """Templates at native size only (scale 1.0), as grayscale arrays."""
    return build_templates(list(named_images), (1.0,))


# Known button positions in the composite (verified via locate):
#   standard: left=968, top=163, w=175, h=43  -> center=(1055, 184)
#   slow:     left=524, top=164, w=208, h=46  -> center=(628, 187)
#   warn:     left=197, top=168, w=28,  h=31  -> center=(211, 183)
CENTERS = {
    "standard.png": (1055, 184),
    "slow.png": (628, 187),
    "warn.png": (211, 183),
}

COMPOSITE_W, COMPOSITE_H = 1265, 369

# Per-button thresholds for zoomed (resized) matching, chosen from measured scores
# on the composite resized by each zoom step:
#   text buttons: correct scale scores ~0.68-0.90, wrong scales stay below ~0.55
#   warn icon:    correct scale scores 0.95+, but a small flat icon produces
#                 spurious wrong-location matches up to ~0.65 at wrong scales
ZOOM_CONF = {"standard.png": 0.6, "slow.png": 0.6, "warn.png": 0.8}


# --------------------
# Tests: find_button
# --------------------

class TestFindButton:
    def test_finds_button_in_full_region(self, composite, slow_img):
        """Find the slow button in the full composite image."""
        location, name = find_button(
            to_gray(composite), 0, 0, native(("slow.png", slow_img)), conf=0.9
        )

        assert location is not None
        assert name == "slow.png"
        assert abs(location.x - 628) <= 2
        assert abs(location.y - 187) <= 2

    def test_finds_button_in_sub_region(self, composite, slow_img):
        """Find the slow button within a cropped sub-region and verify
        absolute coordinate conversion."""
        # Region: x=474, y=114, w=308, h=146 (padding around slow button)
        rx, ry, rw, rh = 474, 114, 308, 146
        gray_crop = to_gray(composite)[ry:ry + rh, rx:rx + rw]

        location, name = find_button(
            gray_crop, rx, ry, native(("slow.png", slow_img)), conf=0.9
        )

        assert location is not None
        assert name == "slow.png"
        # Expected absolute center: (628, 187)
        assert abs(location.x - 628) <= 2
        assert abs(location.y - 187) <= 2

    def test_finds_correct_button_among_multiple(self, composite, standard_img, warn_img):
        """When multiple buttons are in the search list, the correct one is
        identified by name even if another is listed first."""
        # Region containing only the warn button (197, 168, 28, 31)
        # with padding: x=147, y=118, w=128, h=131
        rx, ry, rw, rh = 147, 118, 128, 131
        gray_crop = to_gray(composite)[ry:ry + rh, rx:rx + rw]

        # standard listed first (not present in crop), warn second (present)
        loaded = native(("standard.png", standard_img), ("warn.png", warn_img))
        location, name = find_button(gray_crop, rx, ry, loaded, conf=0.9)

        assert location is not None
        assert name == "warn.png"
        # Expected absolute center: (211, 183)
        assert abs(location.x - 211) <= 2
        assert abs(location.y - 183) <= 2

    def test_returns_none_when_no_match(self, clean_strip, standard_img):
        """When no button is present in the image, should return (None, None)."""
        location, name = find_button(
            to_gray(clean_strip), 0, 0, native(("standard.png", standard_img)), conf=0.9
        )

        assert location is None
        assert name is None

    def test_first_button_in_list_wins_if_both_present(self, composite, standard_img, slow_img):
        """If both buttons appear in the screenshot, the first in the list wins."""
        loaded = native(("standard.png", standard_img), ("slow.png", slow_img))

        location, name = find_button(to_gray(composite), 0, 0, loaded, conf=0.9)

        assert location is not None
        assert name == "standard.png"
        # Expected center for standard: (1055, 184)
        assert abs(location.x - 1055) <= 2
        assert abs(location.y - 184) <= 2

    def test_skips_template_larger_than_haystack(self):
        """A needle bigger than the haystack is skipped, giving (None, None)."""
        tiny = to_gray(Image.new("RGB", (10, 10), color=(128, 128, 128)))
        big_needle = Image.new("RGB", (208, 46), color=(0, 0, 0))

        location, name = find_button(tiny, 0, 0, native(("slow.png", big_needle)), conf=0.9)

        assert location is None
        assert name is None


# --------------------
# Tests: multi-scale templates (browser zoom)
# --------------------

class TestScaledTemplates:
    def test_scales_ordered_closest_to_one_first(self, slow_img):
        """The first template for a button is the native-size one, then the
        nearest zoom steps."""
        templates = build_templates([("slow.png", slow_img)], scales)
        widths = [t.shape[1] for _, t in templates]

        assert len(templates) == len(scales)
        assert widths[0] == slow_img.width  # scale 1.0 first
        # 1.1 and 0.9 are equally far from 1.0 (which one sorts first depends
        # on float rounding), so only require that they are the next two.
        assert set(widths[1:3]) == {
            round(slow_img.width * 1.1),
            round(slow_img.width * 0.9),
        }

    @pytest.mark.parametrize("factor", [s for s in scales if s != 1.0])
    def test_finds_all_buttons_when_page_is_zoomed(
        self, composite, standard_img, slow_img, warn_img, factor
    ):
        """Simulate a different browser zoom by resizing the whole composite,
        then check every button is still found at the right (scaled) spot
        using the real scale list."""
        zoomed = composite.resize(
            (round(composite.width * factor), round(composite.height * factor)),
            Image.LANCZOS,
        )
        gray = to_gray(zoomed)
        bases = {
            "standard.png": standard_img,
            "slow.png": slow_img,
            "warn.png": warn_img,
        }

        for name, base in bases.items():
            templates = build_templates([(name, base)], scales)
            # Resized buttons match less tightly than a native capture, so use
            # the per-button ZOOM_CONF thresholds, not the 0.9 default.
            location, found = find_button(gray, 0, 0, templates, conf=ZOOM_CONF[name])

            expected_x, expected_y = CENTERS[name]
            assert location is not None, f"{name} not found at zoom {factor}"
            assert found == name
            assert abs(location.x - expected_x * factor) <= 4
            assert abs(location.y - expected_y * factor) <= 4

    def test_no_false_positive_on_clean_strip_across_scales(
        self, clean_strip, standard_img, slow_img, warn_img
    ):
        """With every button at every scale, a strip containing no buttons
        must still give no match at the lowered zoom thresholds."""
        gray = to_gray(clean_strip)
        bases = {
            "standard.png": standard_img,
            "slow.png": slow_img,
            "warn.png": warn_img,
        }

        for name, base in bases.items():
            templates = build_templates([(name, base)], scales)
            location, found = find_button(gray, 0, 0, templates, conf=ZOOM_CONF[name])

            assert location is None, f"false positive for {name}"
            assert found is None