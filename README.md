# Slither.io OpenAI Gym

Installation:
- `pip install -e .`
- `npm --prefix ./gym_slither/envs/app install ./gym_slither/envs/app`

Action space: 
- Tuple(angle: Box(-1, 1), sprint: Discrete(2))

Observation space:
- Box(low=0, high=255, shape=(128, 128), dtype=np.uint8)

Based on [k15z/deepsnek](https://github.com/k15z/deepsnek)