# Learned Page Replacement

CSE-307 Operating Systems · Section B · Track 1

This small Python simulation compares FIFO, LRU, Optimal and a decision-tree eviction policy. It does not change the computer's actual RAM.

## Run it

Install Python 3.10 or newer. Extract the ZIP, open this folder in VS Code, and open its terminal.

```bash
python -m venv .venv
```

Windows activation:
```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, skip activation and use `.venv\Scripts\python.exe` instead of `python` in the commands below. On macOS/Linux activate with `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python main.py
python test_policies.py
```

A different experiment:
```bash
python main.py --frames 4 --length 3000 --seed 50 --runs 5
```

Results are overwritten on each run. Copy the results folder before running a different configuration if you want to keep both.

## How it works

- FIFO removes the page loaded earliest. A hit does not reset its loading time.
- LRU removes the page used least recently.
- Optimal removes the page whose next use is farthest away, including pages never used again. It uses future information and is an offline reference, not a deployable policy.
- Learned uses a small decision tree to score each resident page. Its features are time since last access and access count in the previous 50 requests. The highest eviction score wins; ties use LRU.

The tree is trained on eight separate traces (seeds 100–107), using Optimal's victims as labels. Future accesses are used only to construct training labels and evaluate the Optimal reference. Learned-policy inference sees only past requests. The model is frozen during evaluation: it does not retrain after the shift. This makes its generalization limits visible.

Each trace has 24 possible page IDs. In the first half, 85% of requests target pages 0–3; the rest follow a sequential scan. In the second half, requests are uniformly random over all 24 pages. Memory is not reset at the shift. Each policy starts empty and receives the same trace.

## Included run

Defaults: 6 frames, 2,000 requests per trace, five evaluation seeds (42–46). Each phase has 5,000 requests across the five runs. Hit ratio is hits / accesses; page faults are accesses minus hits.

| Policy | Before hit ratio | After hit ratio | Before faults | After faults |
|---|---:|---:|---:|---:|
| FIFO | 75.46% | 24.36% | 1,227 | 3,782 |
| LRU | 83.72% | 24.80% | 814 | 3,760 |
| Optimal | 89.02% | 52.06% | 549 | 2,397 |
| Learned | 86.58% | 25.04% | 671 | 3,748 |

The learned policy loses 61.54 percentage points of hit ratio, the largest absolute drop in this run. Its advantage over LRU before the shift almost disappears afterward. Uniform random requests offer little useful historical signal; with six frames and 24 pages, roughly 25% hits are expected for an online policy. Optimal performs better because it knows the future. These results do not establish a general winner: only one shift scenario and one default frame count were tested, and small post-shift differences should not be treated as strong evidence.

## Files

- `main.py`: generator, policies, training, experiments and chart.
- `test_policies.py`: known-reference checks, capacity checks and Optimal comparison.
- `requirements.txt`: dependencies.
- `results/summary.csv`: pooled before/after metrics.
- `results/per_run.csv`: metrics for each evaluation seed.
- `results/hit_ratio.png`: comparison chart.
- `results/trace_*.csv`: exact evaluation inputs.
- `results/steps_*.csv`: frame contents and eviction decisions for the first evaluation trace (step numbers start at zero).
- `results/results.txt`: readable console summary.
- `NEXT_STEPS_BANGLA.md`: what to do next.

## AI assistance and student review

ChatGPT generated the initial implementation, workload design, tests, documentation and included experiment summary, and ran the supplied configuration. These are supplied starting materials, not a claim that the student independently designed or analyzed the experiment. The student should review the design, run and verify experiments, and write their own analysis before submission, as required by the course brief. Keep this disclosure and update it accurately after making changes.

## Demo outline (3–5 minutes)

1. Explain a hit and a page fault, and why a full memory needs eviction.
2. Show the four choices in `simulate` and the two input features in `features`.
3. Explain the first-half working set and the second-half random shift.
4. Run `python main.py`, then show `results/hit_ratio.png`.
5. Explain why the learned policy loses its advantage and why Optimal is an offline reference.

This ZIP is ready to upload to a GitHub repository, but no GitHub repository has been published. The separately required 2–3 page PDF report and printed copy are not included in this project package.
