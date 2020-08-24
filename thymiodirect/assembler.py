# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Assembler for Aseba VM bytecode
Author: Yves Piguet, EPFL
"""

import thymiodirect
import re
from typing import Callable, Dict, List, Union


class Assembler:

    def __init__(self, remote_node: thymiodirect.connection.RemoteNode, src: str):
        """
        Construct a new Assembler object.

        Args:
            remote_node: Remote node used to predefine constants.
            src: Assembly source code.
        """

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

        def resolve_symbol(a, defs: Dict[str, int], required: bool) -> int:

            def resolve_def(name: str) -> int:
                if not required:
                    return 0
                if re.match("^(0x[0-9a-f]+|[0-9]+)$", name, flags=re.I):
                    return int(name, 0)
                if name not in defs:
                    raise Exception(f'Unknown symbol "{name}"')
                return defs[name]

            if type(a) is str:
                # eval
                val = 0
                minus = False
                offset = 0
                while offset < len(a):
                    r = re.match("(\+|-|[._a-z0-9]+)", a[offset:], re.I)
                    if r is None:
                        raise Exception("Syntax error")
                    s = r.group()
                    if s == "+":
                        minus = False
                    elif s == "-":
                        minus = True
                    else:
                        val += -resolve_def(s) if minus else resolve_def(s)
                    offset += len(s)
                return val

            return a

        def def_to_code(instr: str) -> Callable:
            def register(fun):
                self.instr[instr]["to_code"] = fun
                return fun
            return register

        @def_to_code("dc")
        def to_code_dc(pc: int, args: List[Union[int, str]], label: str, defs: Dict[str, int], phase: int, line: int) -> List[int]:
            return [
                resolve_symbol(a, defs, phase == 1) & 0xffff
                for a in args
            ]

        @def_to_code("equ")
        def to_code_equ(pc, args, label, defs, phase, line):
            if label is None:
                raise Exception(f'No label for pseudo-instruction "equ" (line {line})')
            if defs is not None:
                defs[label] = resolve_symbol(args[0], defs, phase == 1)
                label = None
            return []

        @def_to_code("push.s")
        def to_code_push_s(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg >= 0x1000 or -arg > 0x1000:
                raise Exception(f"Small integer overflow (line {line})")
            return [0x1000 | arg & 0xfff]

        @def_to_code("push")
        def to_code_push(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            return [0x2000, arg & 0xffff]

        @def_to_code("load")
        def to_code_load(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            return [0x3000 | arg & 0xfff]

        @def_to_code("store")
        def to_code_store(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            return [0x4000 | arg & 0xfff]

        @def_to_code("load.ind")
        def to_code_load_ind(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            size_arg = resolve_symbol(args[1], defs, phase == 1)
            return [0x5000 | arg & 0xfff, size_arg & 0xffff]

        @def_to_code("store.ind")
        def to_code_store_ind(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Data address out of range (line {line})")
            size_arg = resolve_symbol(args[1], defs, phase == 1)
            return [0x6000 | arg & 0xfff, size_arg & 0xffff]

        @def_to_code("not")
        def to_code_not(pc, args, label, defs, phase, line):
            raise Exception(f'Unary "not" not implemented in the VM (line {line})')

        @def_to_code("jump")
        def to_code_jump(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            return [0x9000 | (arg - pc) & 0xfff]

        @def_to_code("jump.if.not")
        def to_code_jump_if_not(pc, args, label, defs, phase, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for jump.if.not (line {line})')
            arg = resolve_symbol(args[1], defs, phase == 1)
            return [0xa000 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("do.jump.when.not")
        def to_code_do_jump_when_not(pc, args, label, defs, phase, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for do.jump.when.not (line {line})')
            arg = resolve_symbol(args[1], defs, phase == 1)
            return [0xa100 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("dont.jump.when.not")
        def to_code_do_jump_when_not(pc, args, label, defs, phase, line):
            test_instr = self.instr[args[0]] if args[0] in self.instr else None
            if (test_instr is None
                or "code" not in test_instr
                or len(test_instr["code"]) != 1
                or (test_instr["code"][0] & 0xf000) != 0x8000):
                raise Exception(f'Unknown op "{args[0]}" for dont.jump.when.not (line {line})')
            arg = resolve_symbol(args[1], defs, phase == 1)
            return [0xa300 | (test_instr["code"][0] & 0xff), (arg - pc) & 0xffff]

        @def_to_code("emit")
        def to_code_emit(pc, args, label, defs, phase, line):
            id = resolve_symbol(args[0], defs, phase == 1)
            if id < 0 or id >= 0x1000:
                raise Exception(f"Event id out of range (line {line})")
            addr = resolve_symbol(args[1], defs, phase == 1)
            size = resolve_symbol(args[2], defs, phase == 1)
            return [0xb000 | id & 0xfff, addr & 0xffff, size & 0xffff]

        @def_to_code("callnat")
        def to_code_callnat(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Native call id out of range (line {line})")
            return [0xc000 | arg & 0xfff]

        @def_to_code("callsub")
        def to_code_callsub(pc, args, label, defs, phase, line):
            arg = resolve_symbol(args[0], defs, phase == 1)
            if arg < 0 or arg >= 0x1000:
                raise Exception(f"Subroutine address out of range (line {line})")
            return [0xd000 | arg & 0xfff]

    def node_definitions(self) -> None:
        """Create definition dict based on node variables and native functions.
        """

        defs = {}

        # variables
        for name in self.remote_node.named_variables:
            defs[name] = self.remote_node.var_offset[name]
        defs["_userdata"] = self.remote_node.var_total_size
        defs["_topdata"] = self.remote_node.max_var_size

        # local events
        defs["_ev.init"] = 0xffff
        for i in range(len(self.remote_node.local_events)):
            defs["_ev." + self.remote_node.local_events[i]] = 0xfffe - i

        # native functions
        for i in range(len(self.remote_node.native_functions)):
            defs["_nf." + self.remote_node.native_functions[i]] = i

        return defs

    def assemble(self) -> List[int]:
        """Assemble to bytecode.
        """

        lines = self.src.split("\n")
        defs = self.node_definitions()

        re_blank = re.compile(r"^\s*(;.*)?$")
        re_label = re.compile(r"^\s*([\w_.]+:)\s*(;.*)?$")
        re_instr = re.compile(r"^\s*([\w_.]+:)?\s*([a-z0-9.]+)([-a-zA-Z0-9\s._,+=]*)(;.*)?$")
        re_number = re.compile(r"^(-?[0-9]+|0x[0-9a-fA-F]+)$")

        for phase in (0, 1):
            bytecode = []
            label = None
            for i, line in enumerate(lines):
                if re_blank.match(line):
                    # blank or comment (ignore)
                    continue

                r = re_label.match(line)
                if r:
                    # label without instr
                    label = r[1][0:-1]
                    defs[label] = len(bytecode)
                    continue

                r = re_instr.match(line)
                if r:
                    if r[1]:
                        label = r[1][0:-1]
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
                        raise Exception(f"Unknown instruction {instr_name} (line {i+1})")
                    instr = self.instr[instr_name]
                    if "code" in instr:
                        bytecode += instr["code"]
                    elif "to_code" in instr:
                        args = [
                            int(a, 0) if re_number.match(a) else a
                            for a in args_split
                        ]
                        bytecode += instr["to_code"](len(bytecode), args, label, defs, phase, i + 1)
                    if label is not None and defs[label] != len(bytecode):
                        label = None
                    continue

                print("line", line)
                raise Exception(f"Syntax error (line {i+1})")

        return bytecode

def test(remote_node=None):
    if remote_node is None:
        remote_node = thymiodirect.connection.RemoteNode()

    src = """foo:
    equ 5

    dc end_toc
    dc _ev.init, init
end_toc:

init:
    push foo+1
    stop
"""
    a = Assembler(remote_node, src)
    bc = a.assemble()
    print(src)
    for i, c in enumerate(bc):
        print(f"{i:4d} {c:0=4x}")
