import os 
import numpy as np
import argparse
import torch
import env as Env
from config import Config
from reply_buffer import Reply_Buffer
from agent import Agent
from utils import *

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--massive', dest='massive', help='massive testing',
                        default=False, action='store_true', required=False)
    parser.add_argument('-r', '--random', dest='random_latency', help='use randon latency',
                        default=False, action='store_true', required=False)
    parser.add_argument('-l', '--latency', dest='init_latency', help='initial latency',
                        default=2, type=int, required=False)
    parser.add_argument('-e', '--episode', dest='episode', help='episode of checkpoint',
                        default=50000, type=int, required=False)
    parser.add_argument('-mv', '--model_version', dest='model_version', help='version of model',
                        default=0, type=int, required=False)
    parser.add_argument('-a', '--amplify', dest='bw_amplify', help='amplify bandwidth',
                        default=False, action='store_true')
    # parser.add_argument('-t', '--train', dest='train', help='train policy or not',
    #                     default=True, type=bool)
    args = parser.parse_args()
    if  args.model_version == 1 or args.model_version == 2:
        parser.error('Model version 1 of 2 are not supported.')
    return args
args = parse_args() 

def main():
    massive = args.massive
    episode = args.episode
    model_v = args.model_version
    init_latency = args.init_latency
    random_latency = args.random_latency
    bw_amplify = args.bw_amplify

    env = Env.Live_Streaming(init_latency, testing=True, massive=massive, random_latency=random_latency)
    _, action_dims = env.get_action_info()
    # reply_buffer = Reply_Buffer(Config.reply_buffer_size)
    agent = Agent(action_dims, model_version=model_v)
    if model_v == 0:
        if bw_amplify:
            model_path = './models/logs_m_' + str(model_v) + '/t_0/l_0/latency_Nones_amplified/model-' + str(episode) + '.pth'
        else:
            model_path = './models/logs_m_' + str(model_v) + '/t_0/l_0/latency_Nones/model-' + str(episode) + '.pth'
    agent.restore(model_path)

    if massive:
        if bw_amplify:
            compare_path = Config.a_cdf_dir
            result_path = Config.a_massive_result_files + '/latency_Nones/'
        else:
            compare_path = Config.cdf_dir
            result_path = Config.massive_result_files + 'model_' + str(model_v) + '/latency_Nones/'
        if not os.path.exists(compare_path):
            os.makedirs(compare_path)
        if not os.path.exists(result_path):
             os.makedirs(result_path) 
        if random_latency:
            compare_file = open(compare_path + 'ddqn.txt' , 'w')
        else:
            compare_file = open(compare_path + 'ddqn_' + str(int(init_latency)) +'s.txt' , 'w')
               
        while True:
            # Start testing
            env_end = env.reset(testing=True, bw_amplify=bw_amplify)
            if env_end:
                break
            testing_start_time = env.get_server_time()
            print("Initial latency is: ", testing_start_time)
            tp_trace, time_trace, trace_name, starting_idx = env.get_player_trace_info()
            print("Trace name is: ", trace_name)
            
            # print(massive, episode, model_v)
            log_path = result_path + trace_name 
            log_file = open(log_path, 'w')
            env.act(0, 1, massive=massive)   # Default
            state = env.get_state()
            total_reward = 0.0
            while not env.streaming_finish():
                if model_v == 0:
                    action = agent.testing_take_action(np.array([state]))
                    action_1 = action//action_dims[1]
                    action_2 = action%action_dims[1]
                    reward = env.act(action_1, action_2, log_file, massive=massive)
                    # print(reward)
                    state_new = env.get_state()
                    state = state_new
                    total_reward += reward   
                    # print(action_1, action_2, reward)
            print('File: ', trace_name, ' reward is: ', total_reward) 
            # Get initial latency of player and how long time is used. and tp/time trace
            testing_duration = env.get_server_time() - testing_start_time
            tp_record, time_record = get_tp_time_trace_info(tp_trace, time_trace, starting_idx, testing_duration + env.player.get_buffer())
            log_file.write('\t'.join(str(tp) for tp in tp_record))
            log_file.write('\n')
            log_file.write('\t'.join(str(time) for time in time_record))
            # log_file.write('\n' + str(IF_NEW))
            log_file.write('\n' + str(testing_start_time))
            log_file.write('\n')
            log_file.close()
            env.massive_save(trace_name, compare_file)
            env.save_bw_trace(trace_name, compare_file)
        compare_file.close()
    else:
        # check results log path
        if bw_amplify:
            result_path = Config.a_regular_test_files + 'model_' + str(model_v) + '/latency_' + str(init_latency) + 's/'
        else:
            result_path = Config.regular_test_files + 'model_' + str(model_v) + '/latency_' + str(init_latency) + 's/'
        if not os.path.exists(result_path):
             os.makedirs(result_path) 
        # Start testing
        env_end = env.reset(testing=True, bw_amplify=bw_amplify)
        testing_start_time = env.get_server_time()
        print("Initial latency is: ", testing_start_time)
        tp_trace, time_trace, trace_name, starting_idx = env.get_player_trace_info()
        print("Trace name is: ", trace_name, starting_idx)
        
        # print(massive, episode, model_v)
        log_path = result_path + trace_name + '.txt'
        log_file = open(log_path, 'w')
        env.act(0, 1, log_file)   # Default
        state = env.get_state()
        total_reward = 0.0
        while not env.streaming_finish():
            if model_v == 0:
                action = agent.testing_take_action(np.array([state]))
                action_1 = action//action_dims[1]
                action_2 = action%action_dims[1]
                reward = env.act(action_1, action_2,log_file)
                # print(reward)
                state_new = env.get_state()
                state = state_new
                # print(reward)
                total_reward += reward   
                # print(action_1, action_2, reward)
        print('File: ', trace_name, ' reward is: ', total_reward) 
        # Get initial latency of player and how long time is used. and tp/time trace
        testing_duration = env.get_server_time() - testing_start_time
        tp_record, time_record = get_tp_time_trace_info(tp_trace, time_trace, starting_idx, testing_duration + env.player.get_buffer())
        log_file.write('\t'.join(str(tp) for tp in tp_record))
        log_file.write('\n')
        log_file.write('\t'.join(str(time) for time in time_record))
        # log_file.write('\n' + str(IF_NEW))
        log_file.write('\n' + str(testing_start_time))
        log_file.write('\n')
        log_file.close()

if __name__ == '__main__':
    main()
