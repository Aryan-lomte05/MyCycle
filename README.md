# MyCycle

Private, personal-baseline menstrual health screening. Research paper plus working prototype.

The app learns what is normal for one person, flags changes that may be worth a doctor's attention (a screening flag, never a medical conclusion), keeps raw logs on the phone, and explains what it sees in English, Hindi and Marathi with audio.

Course: 216U50P501 Community Engagement Project with Design Thinking. Guide: Dr. Makarand G. Kulkarni.

## Start here

1. Read `CLAUDE.md` (rules and interface contracts), then `project.md`, then `requirements.md`.
2. Read your own file: `aryan.md`, `liza.md`, `saanj.md` or `aditya.md`.
3. Install the checkers once: `pip install -r requirements-dev.txt`.
4. Run `python scripts/check.py` (or `make check` if you have make). It must be green before every push.
   The Sunday acceptance run uses `python scripts/check.py --strict`, which fails while any placeholder result remains.
5. Slides must pass `python scripts/check_slides.py` (see `requirements.md` section 12 and `docs/SIR_FEEDBACK.md`).

## Status

All results in `results/summary.json` are PLACEHOLDERS until the real pipeline runs. Every result is simulated or preliminary and is labeled as such.

## Layout

See `CLAUDE.md` section 3.
