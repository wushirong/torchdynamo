#!/usr/bin/env pytest
import unittest

import torch

import torchdynamo.testing
from torchdynamo.testing import unsupported

globalmod = torch.nn.ReLU()


def indirectly_unsupported(a, b):
    c = a + b
    return unsupported(a, c)


class SubGraphTests(torchdynamo.testing.TestCase):
    def _common(self, fn, frame_count, op_count):
        torchdynamo.reset()
        v1 = torch.ones(10)
        v2 = torch.ones(10) * -2.0
        correct1 = fn(v1, v2)
        correct2 = fn(v2, v1)
        cnt = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnt):
            r1 = fn(v1, v2)
            r2 = fn(v2, v1)
        self.assertTrue(torchdynamo.testing.same(r1, correct1))
        self.assertTrue(torchdynamo.testing.same(r2, correct2))
        self.assertEqual(cnt.frame_count, frame_count)
        self.assertEqual(cnt.op_count, op_count)

    def test_control_flow1(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            if c1.sum() > c2.sum():
                return c1
            else:
                return c2

        self._common(fn, 1, 5)

    def test_control_flow2(self):
        def fn(a, b):
            if a.sum() > b.sum():
                return 1
            else:
                return 2

        self._common(fn, 1, 3)

    def test_control_flow3(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            m = globalmod
            if c1.sum() > c2.sum():
                return m(c1)
            else:
                return m(c2)

        self._common(fn, 3, 7)

    def test_control_flow4(self):
        def fn(a, b):
            tmp1 = a.sum() > b.sum() and a.sum() > 0
            if tmp1:
                return 1
            else:
                return 2

        self._common(fn, 3, 5)

    def test_control_flow5(self):
        def fn(a, b):
            tmp1 = a.sum() > b.sum() and a.sum() > 0
            tmp2 = a.sum() < b.sum() or b.sum() > 0
            if tmp1 and tmp2:
                return 1, tmp1, tmp2
            else:
                return 2, tmp1, tmp2

        self._common(fn, 6, 13)

    def test_capi_call1(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            return unsupported(c1, c2)

        self._common(fn, 1, 2)

    def test_capi_call2(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            return a - (b - unsupported(c1, c2))

        self._common(fn, 2, 4)

    def test_capi_call3(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            return torchdynamo.testing.unsupported(c1, c2)

        self._common(fn, 1, 2)

    def test_indirect_unsupported1(self):
        def fn(a, b):
            c1 = a - b
            c2 = b - a
            return indirectly_unsupported(c1, c2)

        self._common(fn, 2, 3)

    def test_indirect_unsupported2(self):
        def fn(a, b):
            local_const1 = 7
            local_const2 = 22
            c1 = a - b
            c2 = b - a
            return local_const1 / (local_const2 - indirectly_unsupported(c1, c2))

        self._common(fn, 3, 5)

    def test_indirect_unsupported3(self):
        def fn(a, b):
            args = [a - b, b - a]
            return indirectly_unsupported(*args)

        self._common(fn, 2, 3)

    def test_stack_state1(self):
        def fn(a, b):
            t1 = 1.23 * a
            t2 = 4.56 * a
            c1 = a - b
            c2 = b - a
            return t1 / (t2 - unsupported(c1, c2))

        self._common(fn, 2, 6)

    def test_stack_state2(self):
        def fn(a, b):
            t1 = 1.23 * a
            t2 = 4.56 * a
            c1 = a - b
            c2 = b - a
            return t1 / (t2 - indirectly_unsupported(c1, c2))

        self._common(fn, 3, 7)

    def test_multigraph(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            if x.sum() < 0:
                return x * -1.0
            return x

        self._common(fn, 2, 5)

    def test_extended_args(self):
        too_many_adds = "+".join(["a", "b"] * 256)
        source = (
            f"lambda a, b: ({too_many_adds}+a if a.sum() > 0 else {too_many_adds} - b)"
        )
        self._common(eval(source), 3, 1026)

    def test_resume1(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            x = x + 2.0
            x = unsupported(x, a)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 2, 6)

    def test_resume2(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            x = x + 2.0
            x = indirectly_unsupported(x, a)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 3, 7)

    def test_resume3(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            x = x + 2.0
            x = indirectly_unsupported(x, b=a)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 3, 7)

    def test_resume4(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            x = x + 2.0
            x = indirectly_unsupported(a=x, b=a)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 3, 7)

    def test_resume5(self):
        def fn(a, b):
            x = a + b
            x = x / 2.0
            x = x + 2.0
            print(x)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 2, 6)

    def test_start1(self):
        def fn(a, b):
            print(a)
            x = a + b
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 1, 3)

    def test_start2(self):
        def fn(a, b):
            x = indirectly_unsupported(a, b)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 2, 4)

    def test_start3(self):
        def fn(a, b):
            x = unsupported(a, b)
            x = x + 2.0
            x = x + 2.0
            x = x + 2.0
            return x

        self._common(fn, 1, 3)

    def test_start4(self):
        def fn(a, b, check):
            if check:
                return a + b + 10
            else:
                return a + b - 10

        v1 = torch.randn(10)
        v2 = torch.randn(10)
        f = torch.zeros(1, dtype=torch.int32)
        t = torch.ones(1, dtype=torch.int32)
        correct1 = fn(v1, v2, t)
        correct2 = fn(v1, v2, f)
        cnt = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnt):
            r1 = fn(v1, v2, t)
            r2 = fn(v1, v2, f)
        self.assertTrue(torchdynamo.testing.same(r1, correct1))
        self.assertTrue(torchdynamo.testing.same(r2, correct2))
        self.assertEqual(cnt.frame_count, 3)
        self.assertEqual(cnt.op_count, 4)

    def test_resume_freevars(self):
        c1 = torch.randn(10)
        c2 = torch.randn(10)

        def fn(a, b):
            x = a + b + (c1 - c2)
            x = unsupported(x, x)
            return x + (c1 - c2)

        self._common(fn, 2, 5)

    def test_restore_state(self):
        def fn(a, b):
            len_ = len
            x = a + b
            x = torch.add(unsupported(x, x), 1)
            return a * x + len_(b)

        self._common(fn, 2, 4)

    @unittest.skip("todo")
    def test_nograd(self):
        def fn(a, b):
            x = a + b - 3
            with torch.no_grad():
                x = x + a + b - 4
            return x + a + b - 5

        self._common(fn, 3, 8)
