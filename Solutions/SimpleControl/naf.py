from Agents.AgentGenerator import AgentGenerator
from Environments.SimpleControl.simple_control_problem_env import SimpleControlProblem
from Resolvers.AgentTestingModule import AgentTestingModule

env = SimpleControlProblem(dt=0.5)
epoch_n = 20
episode_n = 500
noise_min = 1e-3
batch_size = 128

tester = AgentTestingModule(env)
path = './../../Tests/SimpleControl/NAF/'

agent_generator = AgentGenerator(env, batch_size, episode_n, noise_min)
tester.test_agent(agent_generator.generate_naf, episode_n, session_len=1000, epoch_n=epoch_n, dt_array=[0.25],
                  path=path)
