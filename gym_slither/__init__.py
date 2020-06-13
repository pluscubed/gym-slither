from gym.envs.registration import register

register(
    id='slither-v0',
    entry_point='gym_slither.envs:SlitherEnv',
)