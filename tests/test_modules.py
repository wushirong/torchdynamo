#!/usr/bin/env pytest

import torch
from torch.nn import functional as F
from torchdynamo._eval_frame import unsupported

import torchdynamo.testing
from . import test_functions


class BasicModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.scale = torch.randn(1, 10)

    def forward(self, x):
        return F.relu(self.linear1(x)) * self.scale


class FnMember(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.activation = F.relu

    def forward(self, x):
        x = self.linear1(x)
        if self.activation:
            x = self.activation(x)
        return x


class FnMemberCmp(torch.nn.Module):
    def __init__(self, activation):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.activation = activation

    def forward(self, x):
        x = self.linear1(x)
        if self.activation is not None:
            x = self.activation(x)
        if self.activation is None:
            x = torch.sigmoid(x)
        return x


class SubmoduleExample(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.layer2 = BasicModule()
        self.scale = torch.randn(1, 10)

    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        return x * self.scale


class IsTrainingCheck(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.linear2 = torch.nn.Linear(10, 10)
        self.train(True)

    def forward(self, x):
        if self.training:
            mod = self.linear1
        else:
            mod = self.linear2
        return F.relu(mod(x))


class IsEvalCheck(IsTrainingCheck):
    def __init__(self):
        super().__init__()
        self.train(False)


class ModuleMethodCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.layer2 = BasicModule()
        self.scale = torch.randn(1, 10)

    def call_and_scale(self, mod, x):
        x = mod(x)
        return x * self.scale

    def forward(self, x):
        x1 = self.call_and_scale(self.layer1, x)
        x2 = self.call_and_scale(self.layer2, x)
        return x1 + x2


class UnsupportedMethodCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.scale = torch.randn(1, 10)

    def call_and_scale(self, mod, x):
        x = mod(x)
        x = x * self.scale
        return unsupported(x, x)

    def forward(self, x):
        x1 = self.call_and_scale(self.layer1, x)
        return x + x1


class UnsupportedModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.scale = torch.randn(1, 10)

    def forward(self, x):
        x = self.layer1(x) * self.scale
        return unsupported(x, x)


class UnsupportedModuleCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.mod = UnsupportedModule()

    def forward(self, x):
        return 1 + self.mod(x * 1.5)


class ModuleStaticMethodCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.layer2 = BasicModule()
        self.scale = torch.randn(1, 10)

    @staticmethod
    def call_and_scale(scale, mod, x):
        x = mod(x)
        return x * scale

    def forward(self, x):
        x1 = self.call_and_scale(self.scale, self.layer1, x)
        x2 = self.call_and_scale(self.scale, self.layer2, x)
        return x1 + x2


class ModuleClassMethodCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = BasicModule()
        self.layer2 = BasicModule()
        self.scale = torch.randn(1, 10)

    @classmethod
    def call_and_scale(cls, scale, mod, x):
        x = mod(x)
        return x * scale

    def forward(self, x):
        x1 = self.call_and_scale(self.scale, self.layer1, x)
        x2 = self.call_and_scale(self.scale, self.layer2, x)
        return x1 + x2


class ModuleProperty(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scale = torch.randn(1, 10)

    @property
    def scale_alias(self):
        return self.scale

    def forward(self, x):
        return x * self.scale_alias


class ConstLoop(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.count = 3

    def forward(self, x):
        for i in range(self.count):
            x = torch.sigmoid(self.linear1(x))
        return x


class ViaModuleCall(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)

    def forward(self, x):
        return test_functions.constant3(torch.sigmoid(self.linear1(x)), x)


class IsNoneLayer(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = torch.nn.Linear(10, 10)
        self.layer2 = None
        self.train(True)

    def forward(self, x):
        if self.layer1 is not None:
            x = self.layer1(x)
        if self.layer2 is not None:
            x = self.layer2(x)
        return x


class LayerList(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = [
            torch.nn.Linear(10, 10),
            torch.nn.ReLU(),
            torch.nn.Linear(10, 10),
        ]

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x


class ModuleList(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = torch.nn.ModuleList(
            [
                torch.nn.Linear(10, 10),
                torch.nn.ReLU(),
                torch.nn.Linear(10, 10),
                torch.nn.ReLU(),
            ]
        )

    def forward(self, x):
        for i in range(len(self.layers)):
            x = self.layers[i](x)

        for layer in self.layers:
            x = layer(x)

        for layer, val in zip(self.layers, (x, x, x, x)):
            x = layer(x) + val

        for layer, val in zip(self.layers, (1, 2, 3, 4)):
            x = layer(x) + val

        for idx, layer in enumerate(self.layers):
            x = layer(x) * idx

        return x


class TensorList(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = (
            torch.randn((1, 10)),
            torch.randn((10, 1)),
            torch.randn((1, 10)),
            torch.randn((10, 1)),
        )

    def forward(self, x):
        for layer in self.layers:
            x = x * layer
        return x


class Children(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.l1 = torch.nn.Linear(10, 10)
        self.l2 = torch.nn.ReLU()
        self.l3 = torch.nn.Linear(10, 10)
        self.l4 = torch.nn.ReLU()

    def forward(self, x):
        for block in self.children():
            x = block(x)
        return x


class IntArg(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = torch.nn.Linear(10, 10)

    def forward(self, x, offset=1):
        x = F.relu(self.layer1(x)) + offset
        return x


class Seq(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(10, 10),
            torch.nn.ReLU(),
            torch.nn.Linear(10, 10),
            torch.nn.ReLU(),
        )

    def forward(self, x):
        return self.layers(x)


class Cfg:
    def __init__(self):
        self.val = 0.5
        self.count = 3


class CfgModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.cfg = Cfg()
        self.layer = torch.nn.Linear(10, 10)

    def forward(self, x):
        for i in range(self.cfg.count):
            x = self.layer(x + self.cfg.val)
        return x


class StringMember(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.mode = "some_string"

    def forward(self, x):
        if self.mode == "some_string":
            return F.relu(self.linear1(x))


class _Block(torch.nn.Module):
    def forward(self, x):
        return 1.5 * torch.cat(x, 1)


class _DenseBlock(torch.nn.ModuleDict):
    _version = 2

    def __init__(
        self,
        num_layers: int = 3,
    ) -> None:
        super().__init__()
        for i in range(num_layers):
            self.add_module("denselayer%d" % (i + 1), _Block())

    def forward(self, init_features):
        features = [init_features]
        for name, layer in self.items():
            new_features = layer(features)
            features.append(new_features)
        return torch.cat(features, 1)


class DenseNetBlocks(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = _DenseBlock()

    def forward(self, x):
        return self.layers(x)


def requires_grad1(module: torch.nn.Module, recurse: bool = False) -> bool:
    requires_grad = any([p.requires_grad for p in module.parameters(recurse)])
    return requires_grad


def requires_grad2(module: torch.nn.Module, recurse: bool = False) -> bool:
    requires_grad = any(p.requires_grad for p in module.parameters(recurse))
    return requires_grad


class ParametersModule1(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = torch.nn.Linear(10, 10)
        self.scale = torch.nn.Parameter(torch.randn(1, 10))

    def forward(self, x):
        if not requires_grad1(self):
            return F.relu(self.linear1(x)) * self.scale
        else:
            return x + 1


class ParametersModule2(ParametersModule1):
    def forward(self, x):
        if not requires_grad2(self):
            return F.relu(self.linear1(x)) * self.scale
        else:
            return x + 1


class ParametersModule3(ParametersModule1):
    def forward(self, x):
        ones = torch.ones(10, dtype=next(self.parameters()).dtype)
        return F.relu(self.linear1(x)) * self.scale + ones


class SuperModule(BasicModule):
    def forward(self, x):
        x = super().forward(x)
        return x + 10.0


class HasAttrModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scale = torch.nn.Parameter(torch.randn(1, 10))

    def forward(self, x):
        x = F.relu(x)
        if hasattr(self, "scale"):
            x *= self.scale
        if hasattr(self, "scale2"):
            x *= self.scale2
        return x


class EnumValues(torch.nn.ModuleDict):
    def __init__(
        self,
        num_layers: int = 3,
    ) -> None:
        super().__init__()
        for i in range(num_layers):
            self.add_module("denselayer%d" % (i + 1), _Block())

    def forward(self, init_features):
        features = [init_features]
        for idx, layer in enumerate(self.values()):
            new_features = layer(features)
            features.append(new_features)
        return torch.cat(features, 1)


def make_test(fn, expected_ops=None):
    def test_fn(self):
        return torchdynamo.testing.standard_test(
            self, fn=fn, nargs=1, expected_ops=expected_ops
        )

    fn.eval()
    return test_fn


class NNModuleTests(torchdynamo.testing.TestCase):
    test_seq = make_test(Seq())
    test_basicmodule1 = make_test(BasicModule())
    test_basicmodule2 = make_test(BasicModule())
    test_submodules1 = make_test(SubmoduleExample())
    test_submodules2 = make_test(SubmoduleExample())
    test_modulemethod1 = make_test(ModuleMethodCall())
    test_modulemethod2 = make_test(ModuleMethodCall())
    test_module_static_method = make_test(ModuleStaticMethodCall())
    test_fnmember = make_test(FnMember())
    test_fnmembercmp1 = make_test(FnMemberCmp(F.relu))
    test_fnmembercmp2 = make_test(FnMemberCmp(None))
    test_constloop = make_test(ConstLoop())
    test_istraining1 = make_test(IsTrainingCheck())
    test_istraining2 = make_test(IsTrainingCheck())
    test_iseval1 = make_test(IsEvalCheck())
    test_iseval2 = make_test(IsEvalCheck())
    test_viamodulecall = make_test(ViaModuleCall())
    test_isnonelayer = make_test(IsNoneLayer())
    test_layerlist = make_test(LayerList())
    test_tensorlist = make_test(TensorList())
    test_intarg = make_test(IntArg())
    test_cfgmod = make_test(CfgModule())
    test_stringmember = make_test(StringMember())
    test_modulelist = make_test(ModuleList())
    test_super1 = make_test(SuperModule())
    test_children = make_test(Children())
    test_densenet = make_test(DenseNetBlocks())
    test_parameters1 = make_test(ParametersModule1())
    test_parameters2 = make_test(ParametersModule2())
    test_parameters3 = make_test(ParametersModule3(), expected_ops=5)
    test_hasattr = make_test(HasAttrModule())
    test_enumvalues = make_test(EnumValues())
    test_module_class_method = make_test(ModuleClassMethodCall())
    test_module_property = make_test(ModuleProperty())

    def test_unsupportedmethod(self):
        m = UnsupportedMethodCall()
        i = torch.randn(10)
        cnt = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnt):
            r = m(i)
        self.assertTrue(torchdynamo.testing.same(r, m(i)))
        self.assertEqual(cnt.op_count, 5)

    def test_unsupportedmodule(self):
        m = UnsupportedModuleCall()
        i = torch.randn(10)
        cnt = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnt):
            r = m(i)
        self.assertTrue(torchdynamo.testing.same(r, m(i)))
        self.assertEqual(cnt.op_count, 6)
