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

Technical takeaways: 
- MTP drastically improved performance in exchange for the modest 0.5 GB VRAM penalty. MTP off ran at about 20 t/s, while MTP on with 4 max draft tokens (over the default 3) raised this to approximately 30 t/s with regular bursts in the mid-30s.
- LM Studio defaults for models were not a good fit, notably hampering performance. Following the official sampling recommendations drastically improved outcomes.


## Why Local AI?

Privacy is one of the primary motivations behind my interest in local inference, although I think the argument deserves a little more nuance than simply keeping prompts off someone else's servers. Local inference is an important component of data privacy, but it isn't a sufficient security guarantee; the model is only one part of a larger execution environment, and evaluating an AI workflow requires looking beyond where inference happens.

#### Inference locality

With hosted models, prompts, source code, retrieved context, and tool outputs are transmitted to infrastructure operated by an external provider. We will suffice to say that my trust in those providers is somewhat *limited*. Local inference changes that trust boundary. Computation happens on hardware I control, preventing sensitive context from leaving my environment. This is particularly relevant for coding agents, for obvious reasons. Of course, this assumes the inference path is genuinely local. Cloud fallbacks, telemetry, and auxiliary services can easily undermine that assumption (see Postscript - Strata).

#### Model provenance

Runtime model acquisition introduces another layer of trust. Where are the weights coming from? Can their integrity be verified? Am I running the exact artifact I intended to download? I'd rather know *exactly* what I'm running and where it came from than treat model acquisition as an inconsequential implementation detail.

#### Agent architecture

This is arguably the most overlooked consideration.

A coding agent isn't simply an LLM with a chat interface. It's another layer that can mediate access to the filesystem, shell, browser, environment variables, external APIs, and other tools. A locally hosted model can still operate within an agent framework that transmits telemetry, delegates embeddings to remote services, or communicates with external providers. Local inference does not guarantee a local workflow. Privacy and security need to be evaluated across the entire execution environment, including network access, tool permissions, and filesystem boundaries.

#### Control is the underlying value proposition

While I might not fully shrug my distaste for some of the aspects of enterprise AI, I cannot deny that it has incredible power and utility. What I find compelling about local inference is operational control. Choosing my models, controlling their acquisition/execution, constraining system access, these are the features I appreciate the most.

I don't (and doubt that I can) necessarily eliminate every external dependency; I just want to better understand, control, and trust the tools I'm utilizing. Local models are impervious to malfeasance - but they offer a degree of autonomy over the infrastructure and data involved in using AI that hosted services inherently abstract away.

#### Postscript - Strata

My initial testing and benchmarking actually began in Strata, rather than LM Studio. I wanted to explore the viability of larger MoE models across VRAM and system memory on relatively modest consumer hardware. The results were remarkable: Qwen3.6-35B-A3B Q6_K_XL managed approximately 50 t/s on my setup.

There were, however, some caveats. While one-shot performance was impressive, integration with Continue's agentic workflow proved considerably less reliable, resulting in substantial churn and lost context. More importantly, I had some reservations about Strata's approach to model acquisition. Its runtime downloading of model weights without explicit user intervention introduced a supply-chain concern that I wasn't comfortable overlooking, especially given the recent history of attacks targeting the AI software ecosystem in the last few weeks (~October 2026). The intent obviously isn't malicious, but it is counterproductive to introduce another opaque trust relationship into my workflow as privacy is among my chief motivations.

I ultimately moved to LM Studio for a more predictable and controlled environment. I still think Strata's approach to MoE resource allocation is compelling, and I'd love to see more transparent model acquisition and verification in future releases. I'd also love to see similar hardware allocation capabilities make their way into LM Studio.
