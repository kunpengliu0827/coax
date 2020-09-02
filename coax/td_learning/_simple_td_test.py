# ------------------------------------------------------------------------------------------------ #
# MIT License                                                                                      #
#                                                                                                  #
# Copyright (c) 2020, Microsoft Corporation                                                        #
#                                                                                                  #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software    #
# and associated documentation files (the "Software"), to deal in the Software without             #
# restriction, including without limitation the rights to use, copy, modify, merge, publish,       #
# distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the    #
# Software is furnished to do so, subject to the following conditions:                             #
#                                                                                                  #
# The above copyright notice and this permission notice shall be included in all copies or         #
# substantial portions of the Software.                                                            #
#                                                                                                  #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING    #
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND       #
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,     #
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,   #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.          #
# ------------------------------------------------------------------------------------------------ #

from copy import deepcopy

from optax import sgd

from .._base.test_case import TestCase
from .._core.value_v import V
from .._core.policy import Policy
from ..utils import get_transition
from ..policy_regularizers import EntropyRegularizer
from ._simple_td import SimpleTD


class TestSimpleTD(TestCase):

    def setUp(self):
        self.transition_discrete = get_transition(self.env_discrete).to_batch()
        self.transition_boxspace = get_transition(self.env_boxspace).to_batch()

    def test_update_discrete(self):
        env = self.env_discrete
        func_v = self.func_v

        v = V(func_v, env.observation_space, random_seed=11)
        v_targ = v.copy()
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0))

        params = deepcopy(v.params)
        function_state = deepcopy(v.function_state)

        updater.update(self.transition_discrete)

        self.assertPytreeNotEqual(params, v.params)
        self.assertPytreeNotEqual(function_state, v.function_state)

    def test_update_boxspace(self):
        env = self.env_boxspace
        func_v = self.func_v

        v = V(func_v, env.observation_space, random_seed=11)
        v_targ = v.copy()
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0))

        params = deepcopy(v.params)
        function_state = deepcopy(v.function_state)

        updater.update(self.transition_boxspace)

        self.assertPytreeNotEqual(params, v.params)
        self.assertPytreeNotEqual(function_state, v.function_state)

    def test_policyreg_discrete(self):
        env = self.env_discrete
        func_v = self.func_v
        func_pi = self.func_pi_discrete
        transition_batch = self.transition_discrete

        v = V(func_v, env.observation_space, random_seed=11)
        pi = Policy(func_pi, env.observation_space, env.action_space, random_seed=17)
        v_targ = v.copy()

        params_init = deepcopy(v.params)
        function_state_init = deepcopy(v.function_state)

        # first update without policy regularizer
        policy_reg = EntropyRegularizer(pi, beta=1.0)
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0))
        updater.update(transition_batch)
        params_without_reg = deepcopy(v.params)
        function_state_without_reg = deepcopy(v.function_state)
        self.assertPytreeNotEqual(params_without_reg, params_init)
        self.assertPytreeNotEqual(function_state_without_reg, function_state_init)

        # reset weights
        v.params = deepcopy(params_init)
        v.function_state = deepcopy(function_state_init)
        self.assertPytreeAlmostEqual(params_init, v.params)
        self.assertPytreeAlmostEqual(function_state_init, v.function_state)

        # then update with policy regularizer
        policy_reg = EntropyRegularizer(pi, beta=1.0)
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0), policy_regularizer=policy_reg)
        updater.update(transition_batch)
        params_with_reg = deepcopy(v.params)
        function_state_with_reg = deepcopy(v.function_state)
        self.assertPytreeNotEqual(params_with_reg, params_init)
        self.assertPytreeNotEqual(function_state_with_reg, function_state_init)
        self.assertPytreeNotEqual(params_with_reg, params_without_reg)
        self.assertPytreeAlmostEqual(function_state_with_reg, function_state_without_reg)  # same!

    def test_policyreg_boxspace(self):
        env = self.env_boxspace
        func_v = self.func_v
        func_pi = self.func_pi_boxspace
        transition_batch = self.transition_boxspace

        v = V(func_v, env.observation_space, random_seed=11)
        pi = Policy(func_pi, env.observation_space, env.action_space, random_seed=17)
        v_targ = v.copy()

        params_init = deepcopy(v.params)
        function_state_init = deepcopy(v.function_state)

        # first update without policy regularizer
        policy_reg = EntropyRegularizer(pi, beta=1.0)
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0))
        updater.update(transition_batch)
        params_without_reg = deepcopy(v.params)
        function_state_without_reg = deepcopy(v.function_state)
        self.assertPytreeNotEqual(params_without_reg, params_init)
        self.assertPytreeNotEqual(function_state_without_reg, function_state_init)

        # reset weights
        v.params = deepcopy(params_init)
        v.function_state = deepcopy(function_state_init)
        self.assertPytreeAlmostEqual(params_init, v.params)
        self.assertPytreeAlmostEqual(function_state_init, v.function_state)

        # then update with policy regularizer
        policy_reg = EntropyRegularizer(pi, beta=1.0)
        updater = SimpleTD(v, v_targ, optimizer=sgd(1.0), policy_regularizer=policy_reg)
        updater.update(transition_batch)
        params_with_reg = deepcopy(v.params)
        function_state_with_reg = deepcopy(v.function_state)
        self.assertPytreeNotEqual(params_with_reg, params_init)
        self.assertPytreeNotEqual(function_state_with_reg, function_state_init)
        self.assertPytreeNotEqual(params_with_reg, params_without_reg)
        self.assertPytreeAlmostEqual(function_state_with_reg, function_state_without_reg)  # same!
