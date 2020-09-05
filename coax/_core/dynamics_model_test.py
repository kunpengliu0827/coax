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

from functools import partial

import gym
import jax
import jax.numpy as jnp
import numpy as onp
import haiku as hk

from .._base.test_case import TestCase
from ..utils import safe_sample
from .dynamics_model import DynamicsModel


discrete = gym.spaces.Discrete(7)
boxspace = gym.spaces.Box(low=0, high=1, shape=(3, 5))
multidiscrete = gym.spaces.MultiDiscrete([11, 5, 7])


def check_onehot(S):
    if jnp.issubdtype(S.dtype, jnp.integer):
        return hk.one_hot(S, discrete.n)
    return S


def func_discrete_type1(S, A, is_training):
    batch_norm = hk.BatchNorm(False, False, 0.99)
    seq = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(discrete.n),
    ))
    X = jax.vmap(jnp.kron)(check_onehot(S), A)
    return {'logits': seq(X)}


def func_discrete_type2(S, is_training):
    batch_norm = hk.BatchNorm(False, False, 0.99)
    seq = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(discrete.n * discrete.n),
        hk.Reshape((discrete.n, discrete.n)),
    ))
    X = check_onehot(S)
    return {'logits': seq(X)}


def func_boxspace_type1(S, A, is_training):
    batch_norm = hk.BatchNorm(False, False, 0.99)
    mu = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(onp.prod(boxspace.shape)),
        hk.Reshape(boxspace.shape),
    ))
    logvar = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(onp.prod(boxspace.shape)),
        hk.Reshape(boxspace.shape),
    ))
    X = jax.vmap(jnp.kron)(check_onehot(S), A)
    return {'mu': mu(X), 'logvar': logvar(X)}


def func_boxspace_type2(S, is_training):
    batch_norm = hk.BatchNorm(False, False, 0.99)
    mu = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(onp.prod(boxspace.shape) * discrete.n),
        hk.Reshape((discrete.n, *boxspace.shape)),
    ))
    logvar = hk.Sequential((
        hk.Flatten(),
        hk.Linear(8), jax.nn.relu,
        partial(hk.dropout, hk.next_rng_key(), 0.25 if is_training else 0.),
        partial(batch_norm, is_training=is_training),
        hk.Linear(8), jnp.tanh,
        hk.Linear(onp.prod(boxspace.shape) * discrete.n),
        hk.Reshape((discrete.n, *boxspace.shape)),
    ))
    X = check_onehot(S)
    return {'mu': mu(X), 'logvar': logvar(X)}


class TestDynamicsModel(TestCase):
    def test_init(self):
        # cannot define a type-2 models on a non-discrete action space
        msg = r"type-2 models are only well-defined for Discrete action spaces"
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_boxspace_type2, boxspace, boxspace)
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_discrete_type2, discrete, boxspace)

        msg = (
            r"func has bad return tree_structure, "
            r"expected: PyTreeDef\(dict\[\['logvar', 'mu'\]\], \[\*,\*\]\), "
            r"got: PyTreeDef\(dict\[\['logits'\]\], \[\*\]\)"
        )
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_discrete_type1, boxspace, discrete)
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_discrete_type2, boxspace, discrete)
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_discrete_type1, boxspace, boxspace)

        msg = (
            r"func has bad return tree_structure, "
            r"expected: PyTreeDef\(dict\[\['logits'\]\], \[\*\]\), "
            r"got: PyTreeDef\(dict\[\['logvar', 'mu'\]\], \[\*,\*\]\)"
        )
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_boxspace_type1, discrete, discrete)
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_boxspace_type2, discrete, discrete)
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(func_boxspace_type1, discrete, boxspace)

        # these should all be fine
        DynamicsModel(func_discrete_type1, discrete, boxspace)
        DynamicsModel(func_discrete_type1, discrete, discrete)
        DynamicsModel(func_discrete_type2, discrete, discrete)
        DynamicsModel(func_boxspace_type1, boxspace, boxspace)
        DynamicsModel(func_boxspace_type1, boxspace, discrete)
        DynamicsModel(func_boxspace_type2, boxspace, discrete)

    # test_call_* ##################################################################################

    def test_call_discrete_discrete_type1(self):
        func = func_discrete_type1
        observation_space = discrete
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        for s_next in p(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_call_discrete_discrete_type2(self):
        func = func_discrete_type2
        observation_space = discrete
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        for s_next in p(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_call_boxspace_discrete_type1(self):
        func = func_boxspace_type1
        observation_space = boxspace
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        for s_next in p(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_call_boxspace_discrete_type2(self):
        func = func_boxspace_type2
        observation_space = boxspace
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        for s_next in p(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_call_discrete_boxspace(self):
        func = func_discrete_type1
        observation_space = discrete
        action_space = boxspace

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        msg = r"input 'A' is required for type-1 dynamics model when action space is non-Discrete"
        with self.assertRaisesRegex(ValueError, msg):
            p(s)

    def test_call_boxspace_boxspace(self):
        func = func_boxspace_type1
        observation_space = boxspace
        action_space = boxspace

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next, logp = p(s, a, return_logp=True)
        print(s_next, logp, observation_space)
        self.assertIn(s_next, observation_space)
        self.assertArraySubdtypeFloat(logp)
        self.assertArrayShape(logp, ())

        msg = r"input 'A' is required for type-1 dynamics model when action space is non-Discrete"
        with self.assertRaisesRegex(ValueError, msg):
            p(s)

    # test_mode_* ##################################################################################

    def test_mode_discrete_discrete_type1(self):
        func = func_discrete_type1
        observation_space = discrete
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        for s_next in p.mode(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_mode_discrete_discrete_type2(self):
        func = func_discrete_type2
        observation_space = discrete
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        for s_next in p.mode(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_mode_boxspace_discrete_type1(self):
        func = func_boxspace_type1
        observation_space = boxspace
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        for s_next in p.mode(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_mode_boxspace_discrete_type2(self):
        func = func_boxspace_type2
        observation_space = boxspace
        action_space = discrete

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        for s_next in p.mode(s):
            print(s_next, observation_space)
            self.assertIn(s_next, observation_space)

    def test_mode_discrete_boxspace(self):
        func = func_discrete_type1
        observation_space = discrete
        action_space = boxspace

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        msg = r"input 'A' is required for type-1 dynamics model when action space is non-Discrete"
        with self.assertRaisesRegex(ValueError, msg):
            p.mode(s)

    def test_mode_boxspace_boxspace(self):
        func = func_boxspace_type1
        observation_space = boxspace
        action_space = boxspace

        s = safe_sample(observation_space, seed=17)
        a = safe_sample(action_space, seed=18)
        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        s_next = p.mode(s, a)
        print(s_next, observation_space)
        self.assertIn(s_next, observation_space)

        msg = r"input 'A' is required for type-1 dynamics model when action space is non-Discrete"
        with self.assertRaisesRegex(ValueError, msg):
            p.mode(s)

    def test_function_state(self):
        func = func_discrete_type1
        observation_space = discrete
        action_space = discrete

        p = DynamicsModel(func, observation_space, action_space, random_seed=19)

        print(p.function_state)
        batch_norm_avg = p.function_state['batch_norm/~/mean_ema']['average']
        self.assertArrayShape(batch_norm_avg, (1, 8))
        self.assertArrayNotEqual(batch_norm_avg, jnp.zeros_like(batch_norm_avg))

    # other tests ##################################################################################

    def test_bad_input_signature(self):
        def badfunc(S, is_training, x):
            pass
        msg = (
            r"func has bad signature; "
            r"expected: func\(S, A, is_training\) or func\(S, is_training\), "
            r"got: func\(S, is_training, x\)"
        )
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(badfunc, boxspace, discrete, random_seed=13)

    def test_bad_output_structure(self):
        def badfunc(S, is_training):
            dist_params = func_discrete_type2(S, is_training)
            dist_params['foo'] = jnp.zeros(1)
            return dist_params
        msg = (
            r"func has bad return tree_structure, "
            r"expected: PyTreeDef\(dict\[\['logits'\]\], \[\*\]\), "
            r"got: PyTreeDef\(dict\[\['foo', 'logits'\]\], \[\*,\*\]\)"
        )
        with self.assertRaisesRegex(TypeError, msg):
            DynamicsModel(badfunc, discrete, discrete, random_seed=13)
