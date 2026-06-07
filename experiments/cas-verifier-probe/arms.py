"""Verifier arms. Each: (reference, candidate) -> (verdict|None, covered, seconds).

verdict: True=equivalent, False=not, None=abstain/uncovered.
The sympy and symbolica arms share ONE structural wrapper (set/tuple/equation
handling); only the scalar-equivalence ENGINE differs. This isolates the
CAS-vs-sympy question at the algebra layer.
"""
import re, time, random

# ---------- normalization ----------
def _clean(s: str) -> str:
    s = s.strip().strip("$").strip()
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\[,;!quad ]+", " ", s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\div", "/")
    s = s.replace("\\pi", "pi").replace("\\infty", "oo")
    # Convert braces from powers/subscripts/roots to parens FIRST, so that
    # \frac numerators/denominators no longer contain inner braces.
    for _ in range(4):
        s2 = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", s)
        s2 = re.sub(r"_\{[^{}]*\}", "", s2)
        s2 = re.sub(r"\\sqrt\[([^\]{}]*)\]\{([^{}]*)\}", r"((\2)^(1/(\1)))", s2)
        s2 = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", s2)
        if s2 == s:
            break
        s = s2
    # \frac{a}{b} -> ((a)/(b))   (loop for nesting)
    for _ in range(6):
        s2 = re.sub(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))", s)
        if s2 == s:
            break
        s = s2
    s = s.replace("{", "(").replace("}", ")")
    s = re.sub(r"\\[a-zA-Z]+", "", s)          # drop remaining latex cmds
    return s.strip()


def _rhs(s: str) -> str:
    """If 'lhs = rhs' (and not '=='), return rhs; else whole string."""
    if s.count("=") == 1 and "==" not in s:
        return s.split("=", 1)[1].strip()
    return s


def _split_top(s: str) -> list:
    """Split on top-level commas (respecting brackets)."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _as_collection(s: str):
    """Return list of element-strings if s is a top-level collection, else None."""
    t = s.strip().strip("$").strip()
    t = t.strip("{}").strip() if (t.startswith("{") and t.endswith("}")) else t
    parts = _split_top(t)
    if len(parts) >= 2:
        return parts
    return None


def _tuple_parts(s: str):
    """If element is a parenthesized tuple, return inner ordered parts."""
    t = s.strip()
    if t.startswith("(") and t.endswith(")"):
        inner = _split_top(t[1:-1])
        if len(inner) >= 2:
            return inner
    return None


# ---------- sympy engine ----------
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor,
)
_SYMPY_TF = standard_transformations + (implicit_multiplication_application, convert_xor)


def _sympy_parse(s: str):
    return parse_expr(_clean(s), transformations=_SYMPY_TF, evaluate=True)


def _sympy_scalar_eq(a: str, b: str):
    try:
        ea, eb = _sympy_parse(a), _sympy_parse(b)
    except Exception:
        return None  # uncovered
    try:
        if sp.simplify(ea - eb) == 0:
            return True
        eq = ea.equals(eb)        # numeric testing inside sympy
        if eq is True:
            return True
        if eq is False:
            return False
        return bool(sp.nsimplify(ea - eb) == 0)
    except Exception:
        return False


def _sympy_canon(s: str):
    try:
        return sp.srepr(sp.simplify(_sympy_parse(s)))
    except Exception:
        return None


# ---------- symbolica engine ----------
from symbolica import E

_VARRE = re.compile(r"(?<![A-Za-z_])[a-zA-Z](?![A-Za-z_(])")

def _sym_parse(s: str):
    return E(_clean(s).replace("**", "^"))

def _symbolica_scalar_eq(a: str, b: str):
    try:
        ea, eb = _sym_parse(a), _sym_parse(b)
    except Exception:
        return None
    try:
        diff = (ea - eb).expand()
        if str(diff) == "0":
            return True
        # Schwartz-Zippel: evaluate at random points over free vars
        vs = sorted(set(_VARRE.findall(_clean(a))) | set(_VARRE.findall(_clean(b))))
        vs = [v for v in vs if v not in ("e", "i")]
        if not vs:
            # constant expr that didn't cancel symbolically -> numeric
            try:
                val = complex(str(diff))
                return abs(val) < 1e-9
            except Exception:
                return False
        ok = True
        for _ in range(8):
            subs = {v: random.uniform(1.3, 2.7) for v in vs}
            ee = diff
            for v, val in subs.items():
                ee = ee.replace(E(v), E(repr(val)))
            try:
                r = complex(str(ee.expand()))
            except Exception:
                return None  # couldn't numerically evaluate -> uncovered
            if abs(r) > 1e-6:
                ok = False
                break
        return ok
    except Exception:
        return False

def _symbolica_canon(s: str):
    try:
        return str(_sym_parse(s).expand())
    except Exception:
        return None


# ---------- shared structural wrapper ----------
def _collection_eq(ref, cand, scalar_eq, canon):
    """Order-independent set-of-tuples / set-of-scalars comparison."""
    ca, cb = _as_collection(ref), _as_collection(cand)
    if ca is None or cb is None:
        return None  # not a collection -> let scalar layer handle
    if len(ca) != len(cb):
        return False
    used = [False] * len(cb)
    for x in ca:
        matched = False
        for j, y in enumerate(cb):
            if used[j]:
                continue
            tx, ty = _tuple_parts(x), _tuple_parts(y)
            if (tx is None) != (ty is None):
                continue
            if tx is not None:
                if len(tx) != len(ty):
                    continue
                if all(scalar_eq(p, q) is True for p, q in zip(tx, ty)):
                    used[j] = matched = True
                    break
            else:
                if scalar_eq(x, y) is True:
                    used[j] = matched = True
                    break
        if not matched:
            return False
    return True


def _make_engine_arm(scalar_eq, canon):
    def arm(ref, cand):
        t0 = time.perf_counter()
        v = _collection_eq(ref, cand, scalar_eq, canon)
        if v is None:
            v = scalar_eq(_rhs(ref), _rhs(cand))
            covered = v is not None
        else:
            covered = True
        return v, covered, time.perf_counter() - t0
    return arm


sympy_arm = _make_engine_arm(_sympy_scalar_eq, _sympy_canon)
symbolica_arm = _make_engine_arm(_symbolica_scalar_eq, _symbolica_canon)


# ---------- regex (string) baseline ----------
def _normstr(s: str) -> str:
    s = _clean(s).lower().replace(" ", "").replace("*", "").replace("\\", "")
    return s

def regex_arm(ref, cand):
    t0 = time.perf_counter()
    v = _normstr(ref) == _normstr(cand)
    return v, True, time.perf_counter() - t0
