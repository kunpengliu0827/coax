import gym
import coax


# pick environment
env = gym.make(...)
env = coax.wrappers.TrainMonitor(env)


# show logs from TrainMonitor
coax.enable_logging()


class MyFuncApprox(coax.FuncApprox):
    def body(self, S):
        # custom haiku function
        ...


# define function approximator
func = coax.MyFuncApprox(env)
v = coax.V(func)
pi = coax.Policy(func)


# specify how to update policy and value function
vanilla_pg = coax.policy_objectives.VanillaPG(pi)
value_td = coax.td_learning.ValueTD(v)


# specify how to trace the transitions
buffer = coax.ExperienceReplayBuffer(env, n=5, gamma=0.9, capacity=256)


for ep in range(100):
    s = env.reset()

    for t in range(env.spec.max_episode_steps):
        a, logp = pi(s, return_logp=True)
        s_next, r, done, info = env.step(a)

        # add transition to buffer
        # N.B. vanilla-pg doesn't use logp but we include it to make it easy to
        # swap in another policy updater that does require it, e.g. ppo-clip
        buffer.add(s, a, r, done, logp)

        # update
        if len(buffer) == buffer.capacity:
            for _ in range(4 * buffer.capacity // 32):  # ~4 passes
                transition_batch = buffer.sample(batch_size=32)
                td_error = value_td.td_error(transition_batch)
                vanilla_pg.update(transition_batch, Adv=td_error)
                value_td.update(transition_batch)

            buffer.clear()

        if done:
            break

        s = s_next