"""
Verify the classifier's label index against known-label crops.

It reads your frozen labels CSV, picks a few known-NC (normal) and known-
abnormal crops, and classifies them. If known-abnormal cells come out
"normal", flip ABNORMAL_INDEX in pipeline/classifier.py.

"""

import csv
import random
from pathlib import Path

from pipeline.classifier import verify_labels, ABNORMAL_INDEX

# >>> EDIT THESE to your local paths <<<
FROZEN_CSV = r"C:\Users\Mahesh Dayarathna\Desktop\UOB\Research\research-artifact\verify_sample\labels_frozen_2026-07-30.csv"
CROPS_DIR  = r"C:\Users\Mahesh Dayarathna\Desktop\UOB\Research\research-artifact\verify_sample"   # folder with the crop images

N_EACH = 6   # how many of each to test


def main():
    rows = list(csv.DictReader(open(FROZEN_CSV, newline="")))
    # only class-labelled rows
    labelled = [r for r in rows if r.get("flag_category") == "class"]

    normal = [r for r in labelled if r["label"] == "NC"]
    abnormal = [r for r in labelled if r["label"] in ("NN", "LN", "BN", "MN", "AP")]

    rng = random.Random(0)
    rng.shuffle(normal); rng.shuffle(abnormal)

    def paths(rows_subset):
        out = []
        for r in rows_subset:
            p = Path(CROPS_DIR) / r["crop_filename"]
            if p.exists():
                out.append(str(p))
            if len(out) >= N_EACH:
                break
        return out

    normal_paths = paths(normal)
    abnormal_paths = paths(abnormal)

    if not normal_paths or not abnormal_paths:
        print("Could not find crop images. Check CROPS_DIR and that the crop "
              "filenames in the CSV exist there.")
        print(f"  normal found: {len(normal_paths)}, abnormal found: {len(abnormal_paths)}")
        return

    verify_labels(normal_paths, abnormal_paths, abnormal_index=ABNORMAL_INDEX)


if __name__ == "__main__":
    main()