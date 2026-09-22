import hashlib
import json
import zipfile

SNUM = [4, "0"]
STXT = [10, ""]
SIDX = [7, "1"]
SWHOLE = [6, "1"]
SPOS = [5, "1"]
SANG = [8, "90"]
SCOL = [9, "#000000"]

BLANK_SVG = (b'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
             b'width="0" height="0" viewBox="0 0 0 0"></svg>')


class Ref(str):
    pass


class B:
    def __init__(self):
        self.blocks = {}
        self.n = 0

    def add(self, opcode, inputs=None, fields=None, shadow=False,
            top=False, x=0, y=0, mutation=None):
        self.n += 1
        bid = Ref("b%d" % self.n)
        d = {"opcode": opcode, "next": None, "parent": None,
             "inputs": inputs or {}, "fields": fields or {},
             "shadow": shadow, "topLevel": top}
        if top:
            d["x"] = x
            d["y"] = y
        if mutation:
            d["mutation"] = mutation
        self.blocks[bid] = d
        return bid

    def link(self, ids):
        ids = [i for i in ids if i]
        for a, c in zip(ids, ids[1:]):
            self.blocks[a]["next"] = c
        return ids[0] if ids else None

    def finalize(self):
        for bid, d in self.blocks.items():
            for inp in d["inputs"].values():
                for el in inp[1:]:
                    if isinstance(el, str) and el in self.blocks:
                        self.blocks[el]["parent"] = bid
            if d["next"]:
                self.blocks[d["next"]]["parent"] = bid


b = B()
V = {}
L = {}
CV = {}
PROCS = {}


def declare(variables=(), lists=(), cloud=()):
    for n in variables:
        V[n] = "var_" + n
    for n in lists:
        L[n] = "list_" + n
    for n in cloud:
        CV[n] = "cloud_" + n.replace("☁ ", "")


def A(v, sh=None):
    if isinstance(v, Ref):
        return [3, str(v), sh or STXT]
    if sh is SCOL and isinstance(v, int):
        v = "#%06x" % v
    t = sh[0] if sh else (4 if isinstance(v, (int, float)) else 10)
    return [1, [t, str(v)]]


def BOOL(v):
    return [2, str(v)]


def var(n):
    return b.add("data_variable", fields={"VARIABLE": [n, V[n]]})


def cvar(n):
    return b.add("data_variable", fields={"VARIABLE": [n, CV[n]]})


def setv(n, v):
    return b.add("data_setvariableto", inputs={"VALUE": A(v)},
                 fields={"VARIABLE": [n, V[n]]})


def changev(n, v):
    return b.add("data_changevariableby", inputs={"VALUE": A(v, SNUM)},
                 fields={"VARIABLE": [n, V[n]]})


def setcv(n, v):
    return b.add("data_setvariableto", inputs={"VALUE": A(v)},
                 fields={"VARIABLE": [n, CV[n]]})


def _lf(n):
    return {"LIST": [n, L[n]]}


def item(n, i):
    return b.add("data_itemoflist", inputs={"INDEX": A(i, SIDX)}, fields=_lf(n))


def addl(n, v):
    return b.add("data_addtolist", inputs={"ITEM": A(v)}, fields=_lf(n))


def repl(n, i, v):
    return b.add("data_replaceitemoflist",
                 inputs={"INDEX": A(i, SIDX), "ITEM": A(v)}, fields=_lf(n))


def insl(n, i, v):
    return b.add("data_insertatlist",
                 inputs={"INDEX": A(i, SIDX), "ITEM": A(v)}, fields=_lf(n))


def dell(n, i):
    return b.add("data_deleteoflist", inputs={"INDEX": A(i, SIDX)}, fields=_lf(n))


def dellall(n):
    return b.add("data_deletealloflist", fields=_lf(n))


def lenl(n):
    return b.add("data_lengthoflist", fields=_lf(n))


def _bin(op, a, c, sh=SNUM):
    return b.add(op, inputs={"NUM1": A(a, sh), "NUM2": A(c, sh)})


def add_(a, c):
    return _bin("operator_add", a, c)


def sub_(a, c):
    return _bin("operator_subtract", a, c)


def mul_(a, c):
    return _bin("operator_multiply", a, c)


def div_(a, c):
    return _bin("operator_divide", a, c)


def mod_(a, c):
    return _bin("operator_mod", a, c)


def round_(x):
    return b.add("operator_round", inputs={"NUM": A(x, SNUM)})


def mathop(f, x):
    return b.add("operator_mathop", inputs={"NUM": A(x, SNUM)},
                 fields={"OPERATOR": [f, None]})


def sqrt_(x):
    return mathop("sqrt", x)


def abs_(x):
    return mathop("abs", x)


def sin_(x):
    return mathop("sin", x)


def cos_(x):
    return mathop("cos", x)


def atan_(x):
    return mathop("atan", x)


def join_(a, c):
    return b.add("operator_join", inputs={"STRING1": A(a, STXT), "STRING2": A(c, STXT)})


def letter(i, s):
    return b.add("operator_letter_of",
                 inputs={"LETTER": A(i, SWHOLE), "STRING": A(s, STXT)})


def length_(s):
    return b.add("operator_length", inputs={"STRING": A(s, STXT)})


def contains(a, c):
    return b.add("operator_contains",
                 inputs={"STRING1": A(a, STXT), "STRING2": A(c, STXT)})


def random_(a, c):
    return b.add("operator_random", inputs={"FROM": A(a, SNUM), "TO": A(c, SNUM)})


def _cmp(op, a, c):
    return b.add(op, inputs={"OPERAND1": A(a, STXT), "OPERAND2": A(c, STXT)})


def lt(a, c):
    return _cmp("operator_lt", a, c)


def gt(a, c):
    return _cmp("operator_gt", a, c)


def eq(a, c):
    return _cmp("operator_equals", a, c)


def not_(x):
    return b.add("operator_not", inputs={"OPERAND": BOOL(x)})


def and_(a, c):
    return b.add("operator_and", inputs={"OPERAND1": BOOL(a), "OPERAND2": BOOL(c)})


def or_(a, c):
    return b.add("operator_or", inputs={"OPERAND1": BOOL(a), "OPERAND2": BOOL(c)})


def _stack(inputs, key, body):
    head = b.link(body)
    if head:
        inputs[key] = [2, str(head)]


def ifb(cond, body):
    i = {"CONDITION": BOOL(cond)}
    _stack(i, "SUBSTACK", body)
    return b.add("control_if", inputs=i)


def ifelse(cond, yes, no):
    i = {"CONDITION": BOOL(cond)}
    _stack(i, "SUBSTACK", yes)
    _stack(i, "SUBSTACK2", no)
    return b.add("control_if_else", inputs=i)


def repeat_(times, body):
    i = {"TIMES": A(times, SWHOLE)}
    _stack(i, "SUBSTACK", body)
    return b.add("control_repeat", inputs=i)


def forever_(body):
    i = {}
    _stack(i, "SUBSTACK", body)
    return b.add("control_forever", inputs=i)


def until_(cond, body):
    i = {"CONDITION": BOOL(cond)}
    _stack(i, "SUBSTACK", body)
    return b.add("control_repeat_until", inputs=i)


def wait_(s):
    return b.add("control_wait", inputs={"DURATION": A(s, SPOS)})


def stop_(opt="this script"):
    return b.add("control_stop", fields={"STOP_OPTION": [opt, None]},
                 mutation={"tagName": "mutation", "children": [],
                           "hasnext": "false" if opt != "other scripts in sprite" else "true"})


def whenflag(x=0, y=0):
    return b.add("event_whenflagclicked", top=True, x=x, y=y)


def whenkey(key, x=0, y=0):
    return b.add("event_whenkeypressed", fields={"KEY_OPTION": [key, None]},
                 top=True, x=x, y=y)


def keypressed(key):
    menu = b.add("sensing_keyoptions", shadow=True, fields={"KEY_OPTION": [key, None]})
    return b.add("sensing_keypressed", inputs={"KEY_OPTION": [1, str(menu)]})


def mousex():
    return b.add("sensing_mousex")


def mousey():
    return b.add("sensing_mousey")


def mousedown():
    return b.add("sensing_mousedown")


def timer():
    return b.add("sensing_timer")


def resettimer():
    return b.add("sensing_resettimer")


def gotoxy(x, y):
    return b.add("motion_gotoxy", inputs={"X": A(x, SNUM), "Y": A(y, SNUM)})


def setx(x):
    return b.add("motion_setx", inputs={"X": A(x, SNUM)})


def sety(y):
    return b.add("motion_sety", inputs={"Y": A(y, SNUM)})


def pointdir(d):
    return b.add("motion_pointindirection", inputs={"DIRECTION": A(d, SANG)})


def movesteps(s):
    return b.add("motion_movesteps", inputs={"STEPS": A(s, SNUM)})


def xpos():
    return b.add("motion_xposition")


def ypos():
    return b.add("motion_yposition")


def hide():
    return b.add("looks_hide")


def penclear():
    return b.add("pen_clear")


def pendown():
    return b.add("pen_penDown")


def penup():
    return b.add("pen_penUp")


def pencolor(c):
    return b.add("pen_setPenColorToColor", inputs={"COLOR": A(c, SCOL)})


def pensize(s):
    return b.add("pen_setPenSizeTo", inputs={"SIZE": A(s, SNUM)})


def penparam(param, value):
    menu = b.add("pen_menu_colorParam", shadow=True,
                 fields={"colorParam": [param, None]})
    return b.add("pen_setPenColorParamTo",
                 inputs={"COLOR_PARAM": [1, str(menu)], "VALUE": A(value, SNUM)})


def define(name, args, body, warp=True, x=0, y=0):
    ids = ["%s_a%d" % (name.replace(" ", "_"), i) for i in range(len(args))]
    code = name + "".join(" %s" for _ in args)
    inputs = {}
    for aid, an in zip(ids, args):
        rep = b.add("argument_reporter_string_number", shadow=True,
                    fields={"VALUE": [an, None]})
        inputs[aid] = [1, str(rep)]
    proto = b.add("procedures_prototype", inputs=inputs, shadow=True,
                  mutation={"tagName": "mutation", "children": [], "proccode": code,
                            "argumentids": json.dumps(ids),
                            "argumentnames": json.dumps(args),
                            "argumentdefaults": json.dumps([""] * len(args)),
                            "warp": "true" if warp else "false"})
    dfn = b.add("procedures_definition", inputs={"custom_block": [1, str(proto)]},
                top=True, x=x, y=y)
    head = b.link(body)
    if head:
        b.blocks[dfn]["next"] = head
    PROCS[name] = (code, ids, warp)
    return dfn


def call(name, *values):
    code, ids, warp = PROCS[name]
    return b.add("procedures_call",
                 inputs={aid: A(v) for aid, v in zip(ids, values)},
                 mutation={"tagName": "mutation", "children": [], "proccode": code,
                           "argumentids": json.dumps(ids),
                           "warp": "true" if warp else "false"})


def arg(name):
    return b.add("argument_reporter_string_number", fields={"VALUE": [name, None]})


def check(project):
    stage, spr = project["targets"][0], project["targets"][1]
    blocks, errs = spr["blocks"], []
    varids = set(stage["variables"]) | set(spr["variables"])
    listids = set(stage["lists"]) | set(spr["lists"])
    seen = set()
    for bid, d in blocks.items():
        for k, inp in d["inputs"].items():
            for el in inp[1:]:
                if isinstance(el, str):
                    if el not in blocks:
                        errs.append("dangling input %s.%s -> %s" % (bid, k, el))
                    else:
                        if blocks[el]["parent"] != bid:
                            errs.append("parent mismatch %s -> %s" % (bid, el))
                        seen.add(el)
        if d["next"]:
            if d["next"] not in blocks:
                errs.append("dangling next %s" % bid)
            else:
                if blocks[d["next"]]["parent"] != bid:
                    errs.append("parent mismatch next %s" % bid)
                seen.add(d["next"])
        for fk, fv in d["fields"].items():
            if fk == "VARIABLE" and fv[1] not in varids:
                errs.append("unknown variable %s" % fv[0])
            if fk == "LIST" and fv[1] not in listids:
                errs.append("unknown list %s" % fv[0])
    for bid, d in blocks.items():
        if d["topLevel"] and (d["parent"] or "x" not in d):
            errs.append("bad topLevel %s" % bid)
        if not d["topLevel"] and bid not in seen:
            errs.append("orphan %s %s" % (bid, d["opcode"]))
    protos = {d["mutation"]["proccode"]: d["mutation"]
              for d in blocks.values() if d["opcode"] == "procedures_prototype"}
    for d in blocks.values():
        if d["opcode"] == "procedures_call":
            m = d["mutation"]
            p = protos.get(m["proccode"])
            if not p:
                errs.append("call to undefined %s" % m["proccode"])
            elif m["argumentids"] != p["argumentids"] or m["warp"] != p["warp"]:
                errs.append("mutation mismatch %s" % m["proccode"])
            elif len(d["inputs"]) != len(json.loads(m["argumentids"])):
                errs.append("wrong arg count %s" % m["proccode"])
    return errs


def build(sprite_name="Main", extensions=None, list_values=None, monitors=None):
    md5 = hashlib.md5(BLANK_SVG).hexdigest()
    costume = {"name": "blank", "bitmapResolution": 1, "dataFormat": "svg",
               "assetId": md5, "md5ext": md5 + ".svg",
               "rotationCenterX": 0, "rotationCenterY": 0}
    b.finalize()
    values = list_values or {}
    stage = {"isStage": True, "name": "Stage",
             "variables": {CV[n]: [n, "0", True] for n in CV},
             "lists": {}, "broadcasts": {}, "blocks": {}, "comments": {},
             "currentCostume": 0, "costumes": [dict(costume, name="backdrop1")],
             "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
             "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None}
    sprite = {"isStage": False, "name": sprite_name,
              "variables": {V[n]: [n, 0] for n in V},
              "lists": {L[n]: [n, values.get(n, [])] for n in L},
              "broadcasts": {}, "blocks": b.blocks, "comments": {},
              "currentCostume": 0, "costumes": [costume], "sounds": [],
              "volume": 100, "layerOrder": 1, "visible": False,
              "x": 0, "y": 0, "size": 100, "direction": 90,
              "draggable": False, "rotationStyle": "all around"}
    return {"targets": [stage, sprite], "monitors": monitors or [],
            "extensions": extensions or [],
            "meta": {"semver": "3.0.0", "vm": "11.0.0", "agent": ""}}


def save(out_path, sprite_name="Main", extensions=None, list_values=None,
         monitors=None, strict=True):
    project = build(sprite_name, extensions, list_values, monitors)
    errs = check(project)
    if errs and strict:
        raise ValueError("structural errors:\n  " + "\n  ".join(errs[:20]))
    md5 = hashlib.md5(BLANK_SVG).hexdigest()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project, separators=(",", ":")))
        z.writestr(md5 + ".svg", BLANK_SVG)
    return {"path": out_path, "blocks": len(b.blocks), "errors": errs}


def reset():
    global b
    b = B()
    V.clear()
    L.clear()
    CV.clear()
    PROCS.clear()
