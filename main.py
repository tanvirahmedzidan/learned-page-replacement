"""Compare page replacement policies on a workload that changes halfway."""

import argparse
import csv
import random
from pathlib import Path
from collections import deque

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier


def make_trace(seed, length=2000, pages=24):
    rng = random.Random(seed)
    half = length // 2

    # First half: frequent access to a small working set.
    first = [
        rng.randrange(4) if rng.random() < 0.85 else i % pages
        for i in range(half)
    ]

    # Second half: random access across all pages.
    second = [
        rng.randrange(pages)
        for _ in range(length - half)
    ]

    return first + second


def features(page, step, last_seen, recent):
    recency = step - last_seen.get(page, -1)
    frequency = recent.count(page)
    return [recency, frequency]


def optimal_victim(frames, future):
    next_use = {
        page: future.index(page) if page in future else float("inf")
        for page in frames
    }
    return max(frames, key=lambda page: next_use[page])


def simulate(trace, capacity, policy, model=None, training=False):
    if capacity < 1:
        raise ValueError("Frame count must be positive")

    frames = []
    last_seen = {}
    loaded = {}
    recent = deque(maxlen=50)

    hits = []
    rows = []
    x = []
    y = []

    for step, page in enumerate(trace):
        hit = page in frames
        victim = None

        if not hit:
            if len(frames) == capacity:
                if training or policy == "Optimal":
                    victim = optimal_victim(
                        frames, trace[step + 1:]
                    )

                    if training:
                        for candidate in frames:
                            x.append(
                                features(
                                    candidate, step, last_seen, recent
                                )
                            )
                            y.append(int(candidate == victim))

                elif policy == "FIFO":
                    victim = min(
                        frames, key=lambda candidate: loaded[candidate]
                    )

                elif policy == "LRU":
                    victim = min(
                        frames,
                        key=lambda candidate: last_seen[candidate]
                    )

                elif policy == "Learned":
                    candidate_features = [
                        features(candidate, step, last_seen, recent)
                        for candidate in frames
                    ]

                    probabilities = model.predict_proba(
                        candidate_features
                    )
                    positive_class = list(model.classes_).index(1)

                    scores = {
                        candidate: probabilities[i, positive_class]
                        for i, candidate in enumerate(frames)
                    }

                    # Use LRU when eviction scores are equal.
                    victim = max(
                        frames,
                        key=lambda candidate: (
                            scores[candidate],
                            step - last_seen[candidate]
                        )
                    )

                else:
                    raise ValueError("Unknown policy")

                frames.remove(victim)

            frames.append(page)
            loaded[page] = step

        last_seen[page] = step
        recent.append(page)
        hits.append(int(hit))

        rows.append([
            step,
            page,
            int(hit),
            "" if victim is None else victim,
            " ".join(map(str, frames))
        ])

    return hits, rows, x, y


def train_model(capacity):
    x = []
    y = []

    # Training seeds are separate from evaluation seeds.
    for seed in range(100, 108):
        _, _, trace_x, trace_y = simulate(
            make_trace(seed, 1000),
            capacity,
            "Optimal",
            training=True
        )
        x.extend(trace_x)
        y.extend(trace_y)

    model = DecisionTreeClassifier(
        max_depth=5,
        min_samples_leaf=25,
        class_weight="balanced",
        random_state=7
    )
    model.fit(x, y)

    return model, len(x)


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--length", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    if (
        not 1 <= args.frames < 24
        or args.length < 100
        or args.runs < 1
    ):
        parser.error(
            "Use 1–23 frames, length >= 100 and runs >= 1"
        )

    evaluation_seeds = set(
        range(args.seed, args.seed + args.runs)
    )
    training_seeds = set(range(100, 108))

    if evaluation_seeds & training_seeds:
        parser.error(
            "Evaluation seeds 100–107 are reserved for training"
        )

    # Save in the user's home folder to avoid the D: folder issue.
    output = Path.home() / "Learned_Page_Results"
    output.mkdir(parents=True, exist_ok=True)

    print("Training the model and running experiments...")

    model, samples = train_model(args.frames)
    policies = ["FIFO", "LRU", "Optimal", "Learned"]

    records = []
    totals = {
        policy: [0, 0, 0, 0]
        for policy in policies
    }

    for seed in range(args.seed, args.seed + args.runs):
        trace = make_trace(seed, args.length)
        half = len(trace) // 2

        write_csv(
            output / f"trace_{seed}.csv",
            ["step", "page", "phase"],
            [
                [
                    i,
                    page,
                    "before" if i < half else "after"
                ]
                for i, page in enumerate(trace)
            ]
        )

        for policy in policies:
            hits, steps, _, _ = simulate(
                trace, args.frames, policy, model
            )

            if seed == args.seed:
                write_csv(
                    output / f"steps_{policy.lower()}.csv",
                    ["step", "page", "hit", "evicted", "frames"],
                    steps
                )

            phases = [
                ("before", hits[:half], 0),
                ("after", hits[half:], 2)
            ]

            for phase, section, slot in phases:
                hit_count = sum(section)
                accesses = len(section)
                faults = accesses - hit_count

                records.append([
                    seed,
                    policy,
                    phase,
                    accesses,
                    hit_count,
                    faults,
                    hit_count / accesses
                ])

                totals[policy][slot] += hit_count
                totals[policy][slot + 1] += accesses

    write_csv(
        output / "per_run.csv",
        [
            "seed", "policy", "phase", "accesses",
            "hits", "faults", "hit_ratio"
        ],
        records
    )

    summary = []

    for policy in policies:
        before_hits, before_count, after_hits, after_count = (
            totals[policy]
        )

        summary.extend([
            [
                policy,
                "before",
                before_count,
                before_hits,
                before_count - before_hits,
                before_hits / before_count
            ],
            [
                policy,
                "after",
                after_count,
                after_hits,
                after_count - after_hits,
                after_hits / after_count
            ]
        ])

    write_csv(
        output / "summary.csv",
        [
            "policy", "phase", "accesses",
            "hits", "faults", "hit_ratio"
        ],
        summary
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    positions = list(range(len(policies)))

    before_ratios = [
        totals[policy][0] / totals[policy][1] * 100
        for policy in policies
    ]
    after_ratios = [
        totals[policy][2] / totals[policy][3] * 100
        for policy in policies
    ]

    ax.bar(
        [i - 0.18 for i in positions],
        before_ratios,
        width=0.36,
        label="Before shift"
    )
    ax.bar(
        [i + 0.18 for i in positions],
        after_ratios,
        width=0.36,
        label="After shift"
    )

    ax.set_xticks(positions, policies)
    ax.set_ylabel("Hit ratio (%)")
    ax.set_ylim(0, 100)
    ax.set_title(
        f"Locality to random access | "
        f"{args.frames} frames | {args.runs} runs"
    )
    ax.legend()

    fig.tight_layout()
    fig.savefig(output / "hit_ratio.png", dpi=180)
    plt.close(fig)

    lines = [
        f"Training candidate rows: {samples}",
        (
            f"Frames: {args.frames}; length: {args.length}; "
            f"evaluation seeds: "
            f"{args.seed}–{args.seed + args.runs - 1}"
        ),
        "",
        (
            "Policy     Before hit%  After hit%  "
            "Before faults  After faults"
        )
    ]

    for policy in policies:
        before_hits, before_count, after_hits, after_count = (
            totals[policy]
        )

        lines.append(
            f"{policy:10} "
            f"{100 * before_hits / before_count:10.2f} "
            f"{100 * after_hits / after_count:11.2f} "
            f"{before_count - before_hits:14} "
            f"{after_count - after_hits:13}"
        )

    result = "\n".join(lines) + "\n"

    (output / "results.txt").write_text(
        result, encoding="utf-8"
    )

    print()
    print(result)
    print(f"Saved tables, chart and step logs in: {output}")


if __name__ == "__main__":
    main()