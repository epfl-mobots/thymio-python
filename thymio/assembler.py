# Assembler for Aseba VM bytecode
# Author: Yves Piguet, EPFL

import re


class Assembler:

    def __init__(self, remote_node, src):
        self.remote_node = remote_node
        self.src = src

        self.instr = {
            "dc": {
                "num_args": -1
            },
            "equ": {
                "num_args": 1
            },
            "stop": {
                "code": [0x0000]
            },
            "push.s": {
                "num_args": 1
            },
            "push": {
                "num_args": 1
            },
            "load": {
                "num_args": 1
            },
            "store": {
                "num_args": 1
            },
            "load.ind": {
                "num_args": 2
            },
            "store.ind": {
                "num_args": 2
            },
            "neg": {
                "code": [0x7000]
            },
            "abs": {
                "code": [0x7001]
            },
            "bitnot": {
                "code": [0x7002]
            },
            "not": {
                # empty
            },
            "sl": {
                "code": [0x8000]
            },
            "asr": {
                "code": [0x8001]
            },
            "add": {
                "code": [0x8002]
            },
            "sub": {
                "code": [0x8003]
            },
            "mult": {
                "code": [0x8004]
            },
            "div": {
                "code": [0x8005]
            },
            "mod": {
                "code": [0x8006]
            },
            "bitor": {
                "code": [0x8007]
            },
            "bitxor": {
                "code": [0x8008]
            },
            "bitand": {
                "code": [0x8009]
            },
            "eq": {
                "code": [0x800a]
            },
            "ne": {
                "code": [0x800b]
            },
            "gt": {
                "code": [0x800c]
            },
            "ge": {
                "code": [0x800d]
            },
            "lt": {
                "code": [0x800e]
            },
            "le": {
                "code": [0x800f]
            },
            "or": {
                "code": [0x8010]
            },
            "and": {
                "code": [0x8011]
            },
            "jump": {
                "num_args": 1
            },
            "jump.if.not": {
                "num_args": 2
            },
            "do.jump.when.not": {
                "num_args": 2
            },
            "dont.jump.when.not": {
                "num_args": 2
            },
            "emit": {
                "num_args": 3
            },
            "callnat": {
                "num_args": 1
            },
            "callsub": {
                "num_args": 1
            },
            "ret": {
                "code": [0xe000]
            },
        }

        def resolve_symbol(a, defs):
            if type(a) is str:
                if defs is None:
                    return 0
                if a not in defs:
                    raise Exception(f'Unknown symbol "{a}"')
                a = defs[a]
            return a

        def def_to_code(instr):
            def register(fun):
                self.instr[instr]["to_code"] = fun
                return fun
            return register

        @def_to_code("dc")
        def to_code_dc(pc, args, label, defs, line):
            return [
                resolve_symbol(a, defs) & 0xffff
                for a in args
            ]

        @def_to_code("equ")
        def to_code_equ(pc, args, label, defs, line):
            if label is None:
                raise Exception(f'No label for pseudo-instruction "equ" (line {line})')
            if defs is not None:
                defs[label] = resolve_symbol(args[0], defs)
            return []

        @def_to_code("push.s")
        def to_code_push_s(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg >= 0x1000 or -arg > 0x1000:
                raise Exception(f"Small integer overflow (line {line})")
            return [0x1000 | arg & 0xfff]

        @def_to_code("push")
        def to_code_push(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            return [0x2000, arg & 0xffff]

        @def_to_code("load")
        def to_code_load(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            return [0x3000 | arg & 0xfff]

        @def_to_code("store")
        def to_code_store(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            return [0x4000 | arg & 0xfff]

        @def_to_code("load.ind")
        def to_code_load_ind(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            size_arg = resolve_symbol(args[1], defs)
            return [0x5000 | arg & 0xfff, size_arg & 0xffff]

        @def_to_code("store.ind")
        def to_code_store_ind(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            size_arg = resolve_symbol(args[1], defs)
            return [0x6000 | arg & 0xfff, size_arg & 0xffff]

        @def_to_code("not")
        def to_code_not(pc, args, label, defs, line):
            raise Exception(f'Unary "not" not implemented in the VM (line {line})')

        @def_to_code("jump")
        def to_code_jump(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            return [0x9000 | (arg - pc) & 0xfff]

        @def_to_code("jump.if.not")
        def to_code_jump_if_not(pc, args, label, defs, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for jump.if.not (line {line})')
            arg = resolve_symbol(args[1], defs)
            return [0xa000 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("do.jump.when.not")
        def to_code_do_jump_when_not(pc, args, label, defs, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for do.jump.when.not (line {line})')
            arg = resolve_symbol(args[1], defs)
            return [0xa100 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("dont.jump.when.not")
        def to_code_do_jump_when_not(pc, args, label, defs, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for dont.jump.when.not (line {line})')
            arg = resolve_symbol(args[1], defs)
            return [0xa300 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("emit")
        def to_code_emit(pc, args, label, defs, line):
            id = resolve_symbol(args[0], defs)
            if id < 0 or id >= 0x1000:
                raise Exception(f"Event id out of range (line {line})")
            addr = resolve_symbol(args[1], defs)
            size = resolve_symbol(args[2], defs)
            return [0xb000 | arg & 0xfff, addr & 0xffff, size & 0xffff]

        @def_to_code("callnat")
        def to_code_callnat(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Native call id out of range (line {line})")
            return [0xc000 | arg & 0xfff]

        @def_to_code("callsub")
        def to_code_callsub(pc, args, label, defs, line):
            arg = resolve_symbol(args[0], defs)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Subroutine address out of range (line {line})")
            return [0xd000 | arg & 0xfff]

    def node_definitions(self):
        """Create definition dict based on node variables and native functions.
        """

        defs = {}

        for name in self.remote_node.named_variables:
            defs[name] = self.remote_node.var_offset[name]
        for i in range(len(self.remote_node.native_functions)):
            defs["_nf." + self.remote_node.native_functions[i]] = i

        return defs

    def assemble(self):
        """Assemble to bytecode.
        """

        lines = self.src.split("\n")
        defs = self.node_definitions()

        re_blank = re.compile(r"^\s*(;.*)?$")
        re_label = re.compile(r"^\s*(\w+:)\s*(;.*)?$")
        re_instr = re.compile(r"^\s*(\w+:)?\s*([a-z0-9.]+)([-a-z0-9\s.,+=]*)(;.*)?$")
        re_number = re.compile(r"^(-?[0-9]+|0x[0-9a-fA-F]+)$")

        for phase in (0, 1):
            bytecode = []
            for i, line in enumerate(lines):
                if re_blank.match(line):
                    # blank or comment (ignore)
                    continue

                r = re_label.match(line)
                if r:
                    # label without instr
                    label = r[1][0:-1]
                    defs[label] = len(bytecode)

                r = re_instr.match(line)
                if r:
                    label = r[1]
                    if label:
                        label = label[0:-1]
                        defs[label] = len(bytecode)
                    instr_name = r[2]
                    instr_args = r[3].strip()
                    if instr_name:
                        if len(instr_args) > 0:
                            args_split = [
                                a.strip()
                                for a1 in instr_args.split(",")
                                for a in a1.strip().split()
                            ]
                        else:
                            args_split = []

                    if instr_name not in self.instr:
                        raise Exception(f"Unknown instruction {instr_name}")
                    instr = self.instr[instr_name]
                    if "code" in instr:
                        bytecode += instr["code"]
                    elif "to_code" in instr:
                        args = [
                            int(a, 0) if re_number.match(a) else a
                            for a in args_split
                        ]
                        bytecode += instr["to_code"](len(bytecode), args, label, defs if phase == 1 else None, i + 1)

        return bytecode

def test():
    import thymio
    remote_node = thymio.connection.RemoteNode()
    src = """
    dc 7
    dc 0xffff, init
    dc 0xfff9, button
    dc 0xffee, timer

init:
    push.s 0
    store 111
    push.s 0
    store 112
    push.s 0
    store 108
    push.s 0
    store 109
    push.s 0
    store 110
    push.s 0
    store 619
    push.s 619
    push.s 0
    store 618
    push.s 618
    push.s 0
    store 617
    push.s 617
    callnat 31
    push.s 0
    store 619
    push.s 619
    push.s 0
    store 618
    push.s 618
    push.s 0
    store 617
    push.s 617
    callnat 32
    push.s 0
    store 619
    push.s 619
    push.s 0
    store 618
    push.s 618
    push.s 0
    store 617
    push.s 617
    callnat 33
    push.s 0
    store 619
    push.s 619
    push.s 0
    store 618
    push.s 618
    push.s 0
    store 617
    push.s 617
    push.s 0
    store 616
    push.s 616
    push.s 0
    store 615
    push.s 615
    push.s 0
    store 614
    push.s 614
    push.s 0
    store 613
    push.s 613
    push.s 0
    store 612
    push.s 612
    callnat 30
    push.s 50
    store 106
    stop

button:
    load 44
    push.s 0
    do.jump.when.not ne 81
    push.s 1
    store 111
    stop

timer:
    load 111
    push.s 0
    jump.if.not ne 88
    push.s 1
    store 112
    load 112
    push.s 0
    jump.if.not ne 108
    push.s 0
    store 619
    push.s 619
    push.s 0
    store 618
    push.s 618
    push.s 0
    store 617
    push.s 617
    callnat 31
    push.s 0
    store 108
    push.s 0
    store 109
    push.s 0
    store 110
    push.s 0
    store 111
    push.s 0
    store 112
    stop
"""
    a = Assembler(remote_node, src)
    bc = a.assemble()
    print(src)
    for i, c in enumerate(bc):
        print(f"{i:4d} {c:0=4x}")
