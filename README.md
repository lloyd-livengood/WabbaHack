# Wabbahack

An automated button-clicker that watches your screen for Nexus target buttons using OpenCV template matching. Built for schmucks like me who can't afford Nexus Premium.
Developed almost exclusively using a local LLM. 

This is mostly 'vibe-coded', I did it to learn about local AI and broaden my knowledge base.

### Model: ukisai/swift-1.5-qwen3.8-27b-gsq-rco-iq3_s-mtp 
### Agent: Continue
### Inference: LM Studio, with honorable mention to Strata

## How It Works

1. Takes a screenshot of the full screen (or a fixed region).
2. Converts it to grayscale and compares against pre-captured button templates at multiple zoom scales (preset to the different browser zooms).
3. A small tkinter status window in the top-right corner shows the current state and contains a Stop button to quit.
4. When a match is found above a confidence threshold, it clicks (or scrolls for the warn button), then parks the mouse over the Stop button so you can grab it and abort quickly.

A cheap frame-diff check (downsampled grayscale comparison) skips expensive matching when the screen hasn't changed.

## Setup

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Requires a graphical display (uses `pyautogui` for screenshots and mouse control). If you're somehow installing a modlist on a headless setup, please seek help.

## Usage

```bash
# Full-screen scan, default settings
python wabbahack.py

# Enable debug logging
python wabbahack.py --debug

# Search only a specific region (x,y,w,h)
python wabbahack.py --region 0,0,1920,1080
```

A small status window appears in the top-right corner. You can click **Stop** to quit, or drag the mouse to a screen corner to trigger pyautogui's failsafe stop.

## Creating Your Own Button Templates

1. Screenshot the button as it appears on your screen (at 100% browser zoom).
2. Crop tightly around the button.
3. Save as a PNG in `assets/`.
4. Add the filename to the `buttons` tuple at the top of `wabbahack.py`, or rename the file accordingly.

The script automatically generates multi-scale versions (75%–150%) to handle browser zoom changes, so you only need one capture per button.

## Running Tests

```bash
pytest -v
```

The test suite uses a composite image (`assets/image_test.png`) containing all three buttons and verifies matching at native size and across all zoom levels.

## Project Structure

```
wabbahack.py          # Main script (CLI, tkinter UI, match loop)
test_wh.py            # Pytest suite for the matching logic
assets/               # Button template images + test composite
requirements.txt      # Python dependencies
```

## My Hardware

CPU / RAM: 9800x3d, 32gb DDR5 memory
GPU: AMD Radeon RX 9060 XT, 16gb VRAM

## Thesis

I've always been a bit of a luddite when it comes to AI, partly because of concerns like environmental impact and privacy. I decided to get hands-on with a small project around local inference — a way to utilize it without running afoul of my objections. 

## Journey
Months ago I made a hacky version of this very script by hand that more or less accomplished the same outcomes, though with far more bugs and wasted compute. 

I gave my program to Claude for a list of bugs and fixes required. I then benchmarked my local model repeatedly on the same prompt to address the fixes while altering parameters like batch sizes, sampling, reasoning level, and templates to find a suitable accuracy and token output. 

Long story short: high reasoning found all of the major issues identified, but took over 8 minutes to do so. Low reasoning found and solved 60% of the errors but still successfully diagnosed the other 40% while coming in at a much quicker 1:30, making it the obvious winner.

At the end of it all I took the winning parameters and ran a full agentic refactor of the project with a final proofread and thumbs up from Claude.

Biggest takeaway: MTP drastically improved performance in exchange for the modest 0.5 GB VRAM penalty. MTP off ran at about 20 t/s, while MTP on with 4 max draft tokens (over the default 3) raised this to approximately 30 t/s with regular bursts in the mid 30s.

Additional notes: LM Studio defaults for models were not a good fit, notably hampering performance. Following the official sampling recommendations drastically improved outcomes.

### Strata
Testing and benchmarking of models actually began in Strata, not LM Studio. I wanted to see what all the fuss about larger MoE models on VRAM and CPU could do on my modest consumer-grade hardware. The results were remarkable, with Qwen3.6-35B-A3B Q6_K_XL running at a blistering 50 t/s. This came with caveats, most notably that the models really didn't interface well with Continue agentically, resulting in lots of churn and lost context (though one-shot capabilities were notable). Strata also has some privacy considerations, as it downloads new weights and models at runtime without without user prompting. This in the wake of the of the recent AI supply chain attacks was simply too large a concern to ignore. I ended up moving to LM Studio for consistency, though I hope Strata addresses these concerns and that LM Studio implements that style of MoE hardware resource allocation tricks soon.
