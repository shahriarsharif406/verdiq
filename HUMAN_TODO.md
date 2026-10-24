# HUMAN_TODO — things only you can do

Everything below needs your accounts, your voice, or your judgment. The project itself is finished and works with **no API key**.

## 0. 5-minute sanity pass (do this first)
```bash
git clone <your repo url> verdiq-check && cd verdiq-check   # or just use this folder
make setup && make data && make test && make run             # Windows without make: python verdiq.py setup|data|test|run
```
Expected: `24 passed` (pytest) and `13 passing` (Hardhat); dashboard at <http://localhost:8501>; every sidebar page loads.
Open **Attack Mode**, press **LAUNCH ATTACK** once. First use takes ~45 s (boots the local chain). You want the green **REAL CONTRACT LIVE** badge and a BLOCKED stamp. If you see **PYTHON MIRROR**, Node/Hardhat is not installed: run `npm install` and retry.

## 1. Create the public GitHub repo and push
1. Review `README.md`: add a "Team" line if you like. The MIT licence says "VERDIQ contributors"; replace with your name in `LICENSE` if you prefer.
2. Make sure your git identity is what you want public: `git config user.name` / `git config user.email`.
3. With the GitHub CLI:
   ```bash
   gh auth login
   gh repo create verdiq --public --source . --remote origin --push
   ```
   or on github.com: **New repository** → name `verdiq` → Public → **no** README/licence → then
   ```bash
   git remote add origin https://github.com/<you>/verdiq.git
   git push -u origin main
   ```
4. Open the repo page and check: banner renders, screenshots render, `LICENSE` is detected as MIT.
5. Paste the repo URL into the *Links* section of `docs/devpost_description.md`.

## 2. Record the 3-5 minute demo video
Follow `docs/demo_script.md` exactly: it has click-by-click steps and talking points for ≈ 4:00.
* Screen: 1920×1080, browser zoom 100 %, hide bookmarks bar, close other tabs except the second tab on `http://localhost:8501/?passport=2507189-2508936`.
* **Warm up first**: open Attack Mode and fire one attack before recording (boots the chain).
* Tools: OBS Studio or Windows **Win+Alt+R** (Xbox Game Bar), or Loom. Use a decent microphone, speak slowly.
* Keep it under 5:00. Climax = Attack Mode (2:05-3:10).
* Say clearly that all data is synthetic and the NDVI series is simulated (the judges' rubric rewards honesty).

## 3. Upload to YouTube
1. studio.youtube.com → **Create → Upload video**.
2. Title: `VERDIQ: Every tonne, verified once. Carbon credit reconciliation + blockchain firewall (IEEE ClimateChain Hackathon)`.
3. Description: paste the first paragraph of `docs/devpost_description.md` + the GitHub link.
4. Visibility: **Public** (or Unlisted if the rules allow). Check "Not made for kids". Copy the URL.

## 4. Create the Devpost project
1. Open the IEEE ClimateChain Global Hackathon page on Devpost → **Join / Register** → **Start a project**. Read the rules page for deadline, eligibility, team size and any AI-use disclosure requirement (I could not check these).
2. Project name: `VERDIQ`; tagline: `Every tonne, verified once.`
3. Track: **Carbon Markets & Emissions Transparency**.
4. Paste `docs/devpost_description.md` into the story fields (sections already match Inspiration / What it does / How we built it / Challenges / What's next; delete the leading "Links" section if the form has dedicated link fields).
5. "Built with": Python, pandas, shapely, networkx, scikit-learn, Streamlit, Plotly, Solidity, Hardhat, ethers.js, Playwright.
6. Links: GitHub repo URL, YouTube URL (and optionally the `?passport=` page if you host it).
7. Image gallery: upload from `docs/screenshots/`: `overview.png`, `attack_mode.png`, `tonne_passport.png`, `fraud_network.png`, `day_end_close.png`, `greenwashing.png`, `time_machine.png`, `overview_bn.png`. Thumbnail: `overview.png` (3:2 crop) or `docs/banner.svg` exported to PNG.
8. Submit, then re-open the public project page and verify the video plays and links work.

## 5. Optional
* **Claude-written case summaries**: `pip install anthropic` and set `ANTHROPIC_API_KEY` before `make run`. Not required; the template fallback is the default. (Model id defaults to `claude-haiku-5-5`; override with `VERDIQ_LLM_MODEL`.)
* **Phone-scannable QR codes**: run the app on your laptop with `VERDIQ_PUBLIC_URL=http://<laptop-LAN-ip>:8501 make run` so a phone on the same Wi-Fi can scan the Passport QR.
* **Hosting a live demo**: Streamlit Community Cloud works for the dashboard (Attack Mode then uses the Python mirror, since Node is not available there; it says so on screen).
* **Sepolia deployment** (stretch, not done): deploy `VerdiqRegistry` with a funded key and add the address to the README.

## 6. Manual checks I recommend
* Watch the video once with sound off: can you follow it from the on-screen text alone?
* Do not claim any real partnership or real data anywhere (the repo already says all data is synthetic).
* Look at `docs/DECISIONS.md` for every assumption I made on your behalf (e.g. equivalents factors, ceilings). Edit anything you disagree with.
* After pushing, clone the repo into a fresh folder and run section 0 once more.
