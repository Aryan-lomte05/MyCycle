# MyCycle end-to-end demo

One command builds one offline HTML file for the smart board:

```
python demo/run_demo.py              # build and open
python demo/run_demo.py --run-tests  # also run all tests and show the real pass count (about 3 minutes)
```

It re-runs the real detector on the demo personas, starts the real backend against a throwaway database,
reads every results file, and writes:

- `MyCycle_Demo.html`: 45 slides, about 18 minutes on autoplay, loops, works without internet. Keys: arrows move,
  P pause/play, F full screen, N speaker notes. Add `#13` to the URL to open the live demo slide paused.
- `SPEAKER_SCRIPT.md`: what to say on each slide, in plain language.
- `COMPARISONS.md`: every design choice compared with the alternatives we tested, with an honest verdict.

No number is typed by hand: everything is read from `results/`. Rebuild after any results change.
The "Who built what" slide is the only hand-edited table (TEAM section in `run_demo.py`).

## Product abstract (Word)

```
npm install docx            # once
python demo/make_abstract.py
```

Writes `MyCycle_Product_Abstract.docx`: abstract, how it works, exact input and output (a real cycle log, the real
detector output, the real backend replies including the refused log upload), a four-person worked example,
data, every results table and figure, the honest comparison of every design choice, and limitations.
