import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

SEED = 2026
REAL = "uci_tw_credit_2005"
SIM = "credit_simulated_v1"
AS_OF = "2005-09-30"
CAPS = (2, 5, 10)
SHA = "56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as src:
        return hashlib.file_digest(src, "sha256").hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else str(x))


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w",
                                     encoding="utf-8", suffix=".tmp") as tmp:
        tmp.write(encode(value) + "\n")
    os.replace(tmp.name, path)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def tie_keys(ids):
    return np.array([digest(f"faro-v1:{i}".encode()) for i in ids])


def log(stage, **fields):
    print(json.dumps({"stage": stage, **fields}, ensure_ascii=False), flush=True)
