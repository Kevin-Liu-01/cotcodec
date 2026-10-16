"""Shared helpers for g3-state-precision-accuracy-v1 (experiments/g3/), EXPLORATORY.

Does a 16-bit GDN recurrent state (vLLM 0.31.0 ``mamba_ssm_cache_dtype`` float16 or bfloat16,
against the checkpoints' float32) change task accuracy at inference? Pure Python (no torch, vLLM
or numpy at import), so the vLLM image, the CPU selftest and the host analysis all import it:

* config loading and validation, and each phase's plan (pilot, main);
* the math task: MATH-500 level-5 prompts, paired request seeds, and a deterministic
  final-answer checker (last ``\\boxed{}`` after the thinking block; MATH-style normalization,
  exact rational/real evaluation of simple LaTeX arithmetic, matrices entry by entry, two-sided
  inequalities against intervals, unordered lists with set braces stripped and \\pm expanded,
  then string equality);
* the long-context task: LongMemEval-S question order and the full-haystack prompt;
* the judge items (AM1's primary judge prompt, ``harness.memcredit_study``).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Sequence
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "g3" / "g3-state-precision-accuracy-v1.yaml"
EXPERIMENT_ID = "g3-state-precision-accuracy-v1"
ARM_NAMES = ("fp32", "fp16", "bf16")
ARM_DTYPES = {"fp32": "auto", "fp16": "float16", "bf16": "bfloat16"}
#: lme_extra: the 4B's long-context arms, run after the main run (no math; see the config).
PHASES = ("pilot", "main", "lme_extra")
TASKS = ("math", "lme")
MODEL_ROOT = Path("/model-cache/cotcodec-models")
LME_CONTAINER_PATH = Path("/inputs/longmemeval_s_cleaned.json")
DATE_FORMAT = "%Y/%m/%d (%a) %H:%M"
#: Request seeds are SEED_STRIDE * seed + question index (identical across arms).
SEED_STRIDE = 100_000
THINK_END = "</think>"


class G3ConfigError(ValueError):
    """The g3 config or its inputs are invalid."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT_ID:
        raise G3ConfigError("not the g3-state-precision-accuracy-v1 config")
    if config.get("claim_level") != "exploratory":
        raise G3ConfigError("g3 is exploratory only")
    if config.get("seeds") != [42, 43, 44]:
        raise G3ConfigError("seeds must be [42, 43, 44]")
    if dict(config.get("arms") or {}) != ARM_DTYPES or tuple(config["arms"]) != ARM_NAMES:
        raise G3ConfigError(f"arms must be {ARM_DTYPES} in order")
    if set(config["tasks"]) != set(TASKS):
        raise G3ConfigError(f"tasks must be {TASKS}")
    for task in TASKS:
        spec = config["tasks"][task]
        sampling = spec["sampling"]
        if sampling["max_tokens"] >= spec["max_model_len"]:
            raise G3ConfigError(f"{task}: max_tokens must leave room for the prompt")
        for key in ("temperature", "top_p", "top_k", "min_p", "presence_penalty"):
            if key not in sampling:
                raise G3ConfigError(f"{task}: sampling.{key} missing")
    if config["engine"].get("enable_prefix_caching"):
        raise G3ConfigError("prefix caching stays off, as in G2b")
    for phase in PHASES:
        if phase in config:
            phase_plan(config, phase)
    margin = float(config["analysis"]["equivalence_margin"])
    if not 0 < margin < 0.5:
        raise G3ConfigError("equivalence margin must be a proportion")
    return config


def phase_plan(config: dict[str, Any], phase: str) -> dict[str, Any]:
    """Arms, math question indices and seeds, long-context question count and seeds, and the
    time budgets of one phase, validated."""

    if phase not in PHASES or phase not in config:
        raise G3ConfigError(f"no {phase!r} phase in the config")
    spec = config[phase]
    arms = list(spec["arms"])
    if not arms or not set(arms) <= set(ARM_NAMES):
        raise G3ConfigError(f"{phase}: unknown arm")
    lme_spec = spec["lme"]
    math_spec = spec.get("math") or {"questions": 0, "seeds": [], "gen_seconds": 0}
    if phase != "lme_extra" and not spec.get("math"):
        raise G3ConfigError(f"{phase}: a math section is required")
    if phase == "lme_extra" and spec.get("math"):
        raise G3ConfigError("lme_extra runs the long-context task only")
    count = int(config["tasks"]["math"]["prompts"]["count"])
    n_math = int(math_spec["questions"])
    if not 0 <= n_math <= count or (phase != "lme_extra" and n_math == 0):
        raise G3ConfigError(f"{phase}: math questions out of range")
    seed_lists = [("lme", lme_spec["seeds"])] + ([("math", math_spec["seeds"])] if n_math else [])
    for key, seeds in seed_lists:
        if not seeds or len(set(seeds)) != len(seeds) or any(int(s) < 0 for s in seeds):
            raise G3ConfigError(f"{phase}.{key}: seeds must be distinct non-negative integers")
    if phase == "lme_extra":
        if arms != list(ARM_NAMES) or [int(s) for s in lme_spec["seeds"]] != config["seeds"][:1]:
            raise G3ConfigError("lme_extra runs every arm with the first declared seed")
        if int(lme_spec["questions"]) > int(config["main"]["lme"]["questions"]):
            raise G3ConfigError("lme_extra's questions are a prefix of the main run's")
    if phase == "main":
        if arms != list(ARM_NAMES):
            raise G3ConfigError("main runs every arm")
        if [int(s) for s in math_spec["seeds"][:3]] != config["seeds"]:
            raise G3ConfigError("main math seeds start with the declared seeds")
        if int(lme_spec["seeds"][0]) != config["seeds"][0]:
            raise G3ConfigError("main long-context seed is the first declared seed")
    return {
        "phase": phase,
        "arms": arms,
        "math_questions": math_subset(count, n_math) if n_math else [],
        "math_seeds": [int(s) for s in math_spec["seeds"]],
        "math_gen_seconds": float(math_spec["gen_seconds"]),
        "lme_questions": int(lme_spec["questions"]),
        "lme_seeds": [int(s) for s in lme_spec["seeds"]],
        "lme_gen_seconds": float(lme_spec["gen_seconds"]),
    }


def math_subset(count: int, n: int) -> list[int]:
    """All indices, or random.Random(42).sample(range(count), n) in index order."""

    if n >= count:
        return list(range(count))
    return sorted(random.Random(42).sample(range(count), n))


def engine_kwargs(
    config: dict[str, Any], model_id: str, model_dir: Path, arm: str, task: str
) -> dict[str, Any]:
    """G2b's rollout engine with this arm's state dtype and this task's max_model_len."""

    if arm not in ARM_NAMES:
        raise G3ConfigError(f"unknown arm {arm!r}")
    if task not in TASKS:
        raise G3ConfigError(f"unknown task {task!r}")
    e = config["engine"]
    return {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": e["dtype"],
        "seed": int(e["seed"]),
        "max_model_len": int(config["tasks"][task]["max_model_len"]),
        "gpu_memory_utilization": float(e["gpu_memory_utilization"]),
        "max_num_seqs": int(e["max_num_seqs"]),
        "max_num_batched_tokens": int(e["max_num_batched_tokens"]),
        "enable_prefix_caching": bool(e["enable_prefix_caching"]),
        "logprobs_mode": e["logprobs_mode"],
        "limit_mm_per_prompt": dict(e["limit_mm_per_prompt"]),
        "disable_log_stats": bool(e["disable_log_stats"]),
        "mamba_ssm_cache_dtype": config["arms"][arm],
    }


def sampling_kwargs(config: dict[str, Any], task: str, seed: int, stop_id: int) -> dict[str, Any]:
    s = config["tasks"][task]["sampling"]
    return {
        "n": 1,
        "temperature": float(s["temperature"]),
        "top_p": float(s["top_p"]),
        "top_k": int(s["top_k"]),
        "min_p": float(s["min_p"]),
        "presence_penalty": float(s["presence_penalty"]),
        "repetition_penalty": float(s["repetition_penalty"]),
        "max_tokens": int(s["max_tokens"]),
        "logprobs": s["logprobs"],
        "seed": int(seed),
        "stop_token_ids": [int(stop_id)],
        "detokenize": False,
    }


def request_seed(seed: int, question_index: int) -> int:
    if not 0 <= question_index < SEED_STRIDE or seed < 0:
        raise G3ConfigError("request seed index out of range")
    return SEED_STRIDE * int(seed) + int(question_index)


# --------------------------------------------------------------------------- math task


def load_math_prompts(config: dict[str, Any]) -> list[dict[str, Any]]:
    spec = config["tasks"]["math"]["prompts"]
    raw = (PROJECT_ROOT / spec["file"]).read_bytes()
    if sha256_bytes(raw) != spec["sha256"]:
        raise G3ConfigError("math prompt file digest differs from the config")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != spec["count"] or [r["prompt_index"] for r in rows] != list(range(len(rows))):
        raise G3ConfigError("math prompt file must hold prompt_index 0..count-1 in order")
    return rows


def math_user_message(row: dict[str, Any], config: dict[str, Any]) -> str:
    return str(row["problem"]) + config["tasks"]["math"]["user_suffix"]


def math_requests(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Submission order: seed, then question (as G2b). Identical for every arm."""

    return [
        {
            "request_id": f"m/q{q:03d}/s{seed}",
            "question_index": q,
            "seed": seed,
            "request_seed": request_seed(seed, q),
        }
        for seed in plan["math_seeds"]
        for q in plan["math_questions"]
    ]


# --------------------------------------------------------------------------- math checker


def last_boxed(text: str) -> str | None:
    """The content of the last ``\\boxed{...}`` (or ``\\fbox{...}``), braces balanced."""

    best = -1
    for pattern in ("\\boxed{", "\\boxed {", "\\fbox{"):
        pos = text.rfind(pattern)
        if pos > best:
            best, width = pos, len(pattern)
    if best < 0:
        return None
    depth, out = 1, []
    for char in text[best + width :]:
        depth += (char == "{") - (char == "}")
        if depth == 0:
            return "".join(out).strip()
        out.append(char)
    return None


def final_answer(completion: str) -> dict[str, Any]:
    """The scored answer: the last boxed answer after the last ``</think>``. A completion with
    no closed thinking block has no answer (it was cut inside its reasoning)."""

    closed = THINK_END in completion
    tail = completion.rsplit(THINK_END, 1)[1] if closed else ""
    answer = last_boxed(tail) if closed else None
    return {
        "thinking_closed": closed,
        "answer": answer,
        "answer_anywhere": last_boxed(completion),
    }


_TEXT_WRAP = re.compile(r"\\(?:text|textbf|mathrm|mbox|textrm)\{([^{}]*)\}")
_UNITS = re.compile(
    r"\\(?:text|mathrm|mbox)\{\s*(?:degrees?|cents?|units?|inches|inch|feet|foot|cm|meters?|"
    r"square\s+units|sq\s+units|dollars?|hours?|minutes?|seconds?|days?|miles?|mph|ways?)\s*\}"
)
_FRAC_SHORT = re.compile(r"\\frac(\d)(\d)")
_FRAC_HALF = re.compile(r"\\frac\{([^{}]+)\}(\d)")
_SQRT_SHORT = re.compile(r"\\sqrt(\d+)")
_SLASH_FRAC = re.compile(r"(?<![\w.])(\d+)/(\d+)(?![\w.])")
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


def normalize_math(text: str | None) -> str:
    """MATH-style normalization of a final answer (string form, before evaluation)."""

    if text is None:
        return ""
    s = str(text).strip()
    s = s.replace("\\\\", "\\cr ")  # a LaTeX row break, kept apart from "\\ " (a space)
    s = s.replace("\n", "").replace("\\!", "").replace("\\,", "").replace("\\;", "")
    s = s.replace("\\:", "").replace("\\ ", " ").replace("~", " ")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\displaystyle", "")
    s = s.replace("dfrac", "frac").replace("tfrac", "frac")
    s = s.replace("^\\circ", "").replace("^{\\circ}", "").replace("°", "")
    s = s.replace("\\%", "").replace("%", "").replace("\\$", "").replace("$", "")
    s = _UNITS.sub("", s)
    s = re.sub(r"\s*(?:degrees?|cents?)\s*$", "", s)
    s = _TEXT_WRAP.sub(r"\1", s)
    s = s.replace("\\leqq", "\\leq").replace("\\geqq", "\\geq")
    s = re.sub(r"\\le(?![a-z])", r"\\leq", s)
    s = re.sub(r"\\ge(?![a-z])", r"\\geq", s)
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = s.strip()
    # "x = 5", "y = 2x + 3": keep the right-hand side of a single short assignment.
    parts = s.split("=")
    if len(parts) == 2 and len(parts[0].strip()) <= 2 and parts[0].strip().isalpha():
        s = parts[1].strip()
    s = re.sub(r"\s+", "", s)
    s = _SQRT_SHORT.sub(r"\\sqrt{\1}", s)
    s = _FRAC_SHORT.sub(r"\\frac{\1}{\2}", s)
    s = _FRAC_HALF.sub(r"\\frac{\1}{\2}", s)
    s = _SLASH_FRAC.sub(r"\\frac{\1}{\2}", s)
    if _THOUSANDS.match(s):
        s = s.replace(",", "")
    if s.startswith("."):
        s = "0" + s
    s = s.replace("{.", "{0.").replace("-.", "-0.")
    if len(s) > 2 and s[0] == "{" and s[-1] == "}" and _balanced(s[1:-1]):
        s = s[1:-1]
    return s


def _balanced(s: str) -> bool:
    depth = 0
    for char in s:
        depth += (char == "{") - (char == "}")
        if depth < 0:
            return False
    return depth == 0


class _Parser:
    """A tiny exact evaluator for normalized LaTeX arithmetic: integers, decimals, \\frac,
    \\sqrt, \\pi, +, -, *, /, ^ (integer powers), parentheses and implicit products. Values are
    (Fraction, float) pairs: exact while rational, a float once \\sqrt or \\pi enters."""

    _TOKEN = re.compile(
        r"\d+\.\d*|\.\d+|\d+|\\frac|\\sqrt|\\pi|\\cdot|\\times|\\div|[-+*/^(){}\[\]]"
    )

    def __init__(self, text: str) -> None:
        self.tokens: list[str] = []
        pos = 0
        while pos < len(text):
            m = self._TOKEN.match(text, pos)
            if m is None:
                raise ValueError(f"unparsable at {pos}")
            self.tokens.append(m.group(0))
            pos = m.end()
        self.i = 0

    def peek(self) -> str | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        tok = self.peek()
        if tok is None or (expected is not None and tok != expected):
            raise ValueError("unexpected token")
        self.i += 1
        return tok

    def parse(self) -> float | Fraction:
        value = self.expr()
        if self.peek() is not None:
            raise ValueError("trailing tokens")
        return value

    def expr(self) -> float | Fraction:
        value = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()
            right = self.term()
            value = value + right if op == "+" else value - right
        return value

    def term(self) -> float | Fraction:
        value = self.unary()
        while True:
            tok = self.peek()
            if tok in ("*", "/", "\\cdot", "\\times", "\\div"):
                self.take()
                right = self.unary()
                value = value / right if tok in ("/", "\\div") else value * right
            elif tok is not None and (
                tok[0].isdigit() or tok in ("(", "{", "\\frac", "\\sqrt", "\\pi")
            ):
                value = value * self.power()
            else:
                return value

    def unary(self) -> float | Fraction:
        if self.peek() == "-":
            self.take()
            return -self.unary()
        if self.peek() == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self) -> float | Fraction:
        base = self.atom()
        if self.peek() == "^":
            self.take()
            exponent = self.atom() if self.peek() != "-" else -self.unary()
            if isinstance(exponent, Fraction) and exponent.denominator == 1:
                if abs(exponent.numerator) > 64:
                    raise ValueError("exponent too large")
                if isinstance(base, Fraction) and base == 0 and exponent < 0:
                    raise ZeroDivisionError
                return base ** int(exponent)
            return float(base) ** float(exponent)
        return base

    def atom(self) -> float | Fraction:
        tok = self.take()
        if tok[0].isdigit() or tok[0] == ".":
            return Fraction(tok)
        if tok in ("(", "{", "["):
            close = {"(": ")", "{": "}", "[": "]"}[tok]
            value = self.expr()
            self.take(close)
            return value
        if tok == "\\pi":
            return math.pi
        if tok == "\\frac":
            num = self.atom()
            den = self.atom()
            return num / den
        if tok == "\\sqrt":
            index = None
            if self.peek() == "[":
                self.take()
                index = self.expr()
                self.take("]")
            value = self.atom()
            if index is not None:
                if value < 0 or index <= 0:
                    raise ValueError("bad root")
                return float(value) ** (1.0 / float(index))
            if value < 0:
                raise ValueError("negative root")
            if isinstance(value, Fraction):
                root_n, root_d = math.isqrt(value.numerator), math.isqrt(value.denominator)
                if root_n * root_n == value.numerator and root_d * root_d == value.denominator:
                    return Fraction(root_n, root_d)
            return math.sqrt(float(value))
        raise ValueError(f"unexpected {tok}")


def evaluate(text: str) -> float | Fraction | None:
    """The value of a normalized answer if it is plain arithmetic, else None."""

    if not text or len(text) > 200:
        return None
    mixed = re.fullmatch(r"(-?)(\d+)\\frac\{(\d+)\}\{(\d+)\}", text)
    if mixed:
        sign = -1 if mixed.group(1) else 1
        whole, num, den = (int(mixed.group(k)) for k in (2, 3, 4))
        if den and num < den:
            return sign * (whole + Fraction(num, den))
    try:
        return _Parser(text).parse()
    except (ValueError, ZeroDivisionError, OverflowError, ArithmeticError):
        return None


def _values_equal(a: float | Fraction, b: float | Fraction) -> bool:
    if isinstance(a, Fraction) and isinstance(b, Fraction):
        return a == b
    fa, fb = float(a), float(b)
    return math.isclose(fa, fb, rel_tol=1e-9, abs_tol=1e-12)


def _split_top_level(s: str) -> list[str]:
    parts, depth, current = [], 0, []
    for char in s:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def _atom_equiv(a: str, b: str) -> bool:
    if a == b:
        return True
    va, vb = evaluate(a), evaluate(b)
    return va is not None and vb is not None and _values_equal(va, vb)


#: A matrix after normalization (row breaks are "\\cr", columns "&").
_MATRIX = re.compile(r"^\\begin\{([pbBvV]?matrix)\}(.*)\\end\{\1\}$")
#: A variable in a two-sided inequality: one letter or a command such as \lambda.
_VAR = r"(?:[a-zA-Z]|\\[a-zA-Z]+)"
_INEQ_UP = re.compile(rf"^(.+?)(<|\\leq){_VAR}(<|\\leq)(.+)$")
_INEQ_DOWN = re.compile(rf"^(.+?)(>|\\geq){_VAR}(>|\\geq)(.+)$")


def _strip_set_braces(s: str) -> str:
    """Drop one pair of outer set braces ("\\{...\\}" is "{...}" after normalization)."""

    s = s.replace("\\lbrace", "{").replace("\\rbrace", "}")
    if len(s) > 2 and s[0] == "{" and s[-1] == "}" and _balanced(s[1:-1]):
        s = s[1:-1]
    return s


def _expand_pm(item: str) -> list[str]:
    """An item with exactly one \\pm (or \\mp) as its two values, the sign put in place:
    "1\\pm\\sqrt{19}" -> ["1+\\sqrt{19}", "1-\\sqrt{19}"]; anything else unchanged."""

    if item.count("\\pm") + item.count("\\mp") != 1:
        return [item]
    token, signs = ("\\pm", ("+", "-")) if "\\pm" in item else ("\\mp", ("-", "+"))
    left, right = item.split(token)
    if not right:
        return [item]
    if not left:
        return [
            right if signs[0] == "+" else "-" + right,
            "-" + right if signs[1] == "-" else right,
        ]
    return [left + signs[0] + right, left + signs[1] + right]


def _list_items(s: str) -> list[str]:
    """An unbracketed answer as its items: set braces stripped, split at top-level commas, and
    each item with one \\pm expanded into its two values."""

    items: list[str] = []
    for part in _split_top_level(_strip_set_braces(s)):
        items.extend(_expand_pm(part))
    return items


def _multiset_equiv(pa: list[str], pb: list[str]) -> bool:
    if len(pa) != len(pb):
        return False
    remaining = list(pb)
    for item in pa:
        match = next((j for j, other in enumerate(remaining) if _atom_equiv(item, other)), None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def _matrix(s: str) -> list[list[str]] | None:
    m = _MATRIX.match(s)
    if m is None:
        return None
    rows = m.group(2).split("\\cr")
    if rows and rows[-1] == "":
        rows.pop()
    return [row.split("&") for row in rows]


def _interval(s: str) -> tuple[str, str, str, str] | None:
    """A bracketed pair "(a,b]" as (left bracket, a, b, right bracket)."""

    if len(s) >= 5 and s[0] in "([" and s[-1] in ")]":
        parts = _split_top_level(s[1:-1])
        if len(parts) == 2 and all(parts):
            return (s[0], parts[0], parts[1], s[-1])
    return None


def _inequality_interval(s: str) -> tuple[str, str, str, str] | None:
    """A two-sided inequality as an interval: "3<\\lambda\\leq4" -> ("(", "3", "4", "]");
    "4\\geqx>3" -> ("(", "3", "4", "]")."""

    m = _INEQ_UP.match(s)
    if m is not None:
        a, op1, op2, b = m.groups()
        return ("(" if op1 == "<" else "[", a, b, ")" if op2 == "<" else "]")
    m = _INEQ_DOWN.match(s)
    if m is not None:
        b, op1, op2, a = m.groups()
        return ("(" if op2 == ">" else "[", a, b, ")" if op1 == ">" else "]")
    return None


def math_equiv(prediction: str | None, reference: str) -> bool:
    """Whether a final answer matches the reference (checker v2).

    In order: normalized string equality or exact value equality for plain arithmetic; matrices
    entry by entry; a two-sided inequality against an interval (bracket types and end points);
    for an unbracketed reference, the answers as unordered lists after stripping set braces and
    expanding one \\pm per item into its two values. Other tuples, intervals and expressions with
    variables compare as strings. (Checker v1 lacked the matrix, inequality, set-brace and \\pm
    steps; program/evidence/2026-10-16/g3-state-precision-accuracy/checker-v1/.)"""

    if prediction is None:
        return False
    a, b = normalize_math(prediction), normalize_math(reference)
    if not a:
        return False
    if _atom_equiv(a, b):
        return True
    ma, mb = _matrix(a), _matrix(b)
    if ma is not None or mb is not None:
        if ma is None or mb is None or [len(r) for r in ma] != [len(r) for r in mb]:
            return False
        return all(
            _atom_equiv(x, y)
            for ra, rb in zip(ma, mb, strict=True)
            for x, y in zip(ra, rb, strict=True)
        )
    qa, qb = _inequality_interval(a), _inequality_interval(b)
    if qa is not None or qb is not None:
        ia = qa if qa is not None else _interval(a)
        ib = qb if qb is not None else _interval(b)
        if ia is None or ib is None:
            return False
        return (
            ia[0] == ib[0]
            and ia[3] == ib[3]
            and _atom_equiv(ia[1], ib[1])
            and _atom_equiv(ia[2], ib[2])
        )
    bracketed = b[:1] in ("(", "[") and b[-1:] in (")", "]")
    if not bracketed:
        pa, pb = _list_items(a), _list_items(b)
        if len(pa) > 1 or len(pb) > 1:
            return _multiset_equiv(pa, pb)
    return False


def g2b_string_match(prediction: str | None, reference: str) -> bool:
    """G2b's light string match (scripts/analyze_g2b_state_dtype.py normalize_answer)."""

    def norm(value: str | None) -> str:
        text = value or ""
        for old, new in (
            ("\\left", ""),
            ("\\right", ""),
            ("\\!", ""),
            ("\\,", ""),
            ("$", ""),
            ("dfrac", "frac"),
            ("tfrac", "frac"),
        ):
            text = text.replace(old, new)
        return re.sub(r"\s+", "", text)

    return prediction is not None and norm(prediction) == norm(reference)


# --------------------------------------------------------------------------- long-context task


def load_lme(path: Path, config: dict[str, Any], verify: bool = True) -> list[dict[str, Any]]:
    spec = config["tasks"]["lme"]["source"]
    if verify:
        if path.stat().st_size != int(spec["size_bytes"]):
            raise G3ConfigError("LongMemEval-S size differs from the config")
        if sha256_file(path) != spec["sha256"]:
            raise G3ConfigError("LongMemEval-S digest differs from the config")
    return json.loads(path.read_text(encoding="utf-8"))


def lme_order(records: Sequence[dict[str, Any]], seed: int) -> list[str]:
    """Non-abstention question ids: shuffled within type (ids sorted first), then types
    interleaved by (rank + 0.5) / type size, ties by type name."""

    by_type: dict[str, list[str]] = {}
    for rec in records:
        qid = str(rec["question_id"])
        if qid.endswith("_abs"):
            continue
        by_type.setdefault(str(rec["question_type"]), []).append(qid)
    keyed = []
    for qtype in sorted(by_type):
        ids = sorted(by_type[qtype])
        random.Random(f"{seed}:{qtype}").shuffle(ids)
        for rank, qid in enumerate(ids):
            keyed.append(((rank + 0.5) / len(ids), qtype, qid))
    return [qid for _, _, qid in sorted(keyed)]


def lme_message(record: dict[str, Any], config: dict[str, Any]) -> str:
    """The full haystack, sessions sorted by date (then file order), then the question."""

    t = config["tasks"]["lme"]["template"]
    dates = record["haystack_dates"]
    sessions = record["haystack_sessions"]
    if len(dates) != len(sessions):
        raise G3ConfigError(f"{record['question_id']}: dates and sessions differ in length")
    order = sorted(
        range(len(sessions)), key=lambda i: (datetime.strptime(dates[i], DATE_FORMAT), i)
    )
    blocks = []
    for number, i in enumerate(order, 1):
        lines = [t["session"].format(number=number, date=dates[i])]
        for turn in sessions[i]:
            lines.append(t["turn"].format(role=turn["role"], content=str(turn["content"]).strip()))
        blocks.append("\n".join(lines))
    tail = t["tail"].format(question_date=record["question_date"], question=record["question"])
    return t["head"] + "\n\n".join(blocks) + tail


def lme_requests(config: dict[str, Any], plan: dict[str, Any], order: Sequence[str]) -> list[dict]:
    ids = list(order)[: plan["lme_questions"]]
    if len(ids) != plan["lme_questions"]:
        raise G3ConfigError("not enough long-context questions")
    return [
        {
            "request_id": f"l/{qid}/s{seed}",
            "question_id": qid,
            "question_index": index,
            "seed": seed,
            "request_seed": request_seed(seed, index),
        }
        for seed in plan["lme_seeds"]
        for index, qid in enumerate(ids)
    ]


def reply_text(completion: str) -> str:
    """A non-thinking reply with any (empty) thinking block removed."""

    text = completion.rsplit(THINK_END, 1)[1] if THINK_END in completion else completion
    return text.strip()


# --------------------------------------------------------------------------- judge


def judge_items(
    questions: dict[str, dict[str, Any]], replies: Sequence[dict[str, Any]], idk: str
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply), then per question the reference answer
    (expect 1) and the "I don't know." reply (expect 0), in canonical order."""

    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for reply in replies:
        key = (str(reply["question_id"]), str(reply["reply"]).strip())
        seen.setdefault(key, {"question_id": key[0], "response": key[1], "source": "reader"})
    items = [seen[k] for k in sorted(seen)]
    for qid in sorted({k[0] for k in seen}):
        items.append(
            {
                "question_id": qid,
                "response": str(questions[qid]["answer"]).strip(),
                "source": "validation:reference",
                "expected": 1,
            }
        )
        items.append(
            {"question_id": qid, "response": idk, "source": "validation:idk", "expected": 0}
        )
    for index, item in enumerate(items):
        item["index"] = index
        item["question_type"] = questions[item["question_id"]]["question_type"]
    return items


def judge_message(question: dict[str, Any], response: str) -> str:
    from harness import memcredit_study as ms

    return ms.judge_prompt(
        str(question["question_type"]),
        str(question["question"]),
        str(question["answer"]),
        response,
    )


def parse_judgment(reply: str) -> tuple[int, bool]:
    from harness import memcredit_study as ms

    return ms.parse_judgment(reply)


def contains_answer(reply: str, answer: Any) -> int:
    from harness import memcredit as mc

    return mc.contains_answer(reply, answer)
