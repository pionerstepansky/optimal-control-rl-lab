from Agents.AgentGenerator import AgentGenerator
from Environments.DubinsCar.DubinsCar import DubinsCar_SymmetricActionInterval as DubinsCar
from Resolvers.AgentTestingModule import AgentTestingModule

env = DubinsCar(dt=1, inner_step_n=100)
epoch_n = 10
episode_n = 500
noise_min = 1e-3

tester = AgentTestingModule(env)
path = './../../Tests/DubinsCar/NAF/'

agent_generator = AgentGenerator(env, episode_n, noise_min)
tester.test_agent(agent_generator.generate_naf, episode_n, session_len=1000, epoch_n=epoch_n, dt_array=[1],
                  path=path)