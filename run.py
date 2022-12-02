import shutil
import os
import sys
import subprocess
import time
import torch

import running_average
import bayesian_optimization
import config

src = './template'
dst = './runtime'
model_dst = './runtime/constant/geometry/model.obj'

avg_window_start = 450
avg_window_end = 500

averages_file = './data/averages.csv'
raw_data_path = './data/forces'

foam_log_path = './foam_log.txt'

tkwargs = bayesian_optimization.tkwargs

def optimize_target(batches, initial_sample_size=10, fake_simulation=False):   
    """
    Optimize the model for the target drag and lift values.

    Use `fake_simulation` to avoid actually simulating the model in order to test
    simulated annealing.
    """ 
    print('\nBegin optimizing with parameters: ')
    print('Initial Sample Size: %i' %(initial_sample_size,))
    print('Batches: %i' %(batches,))

    # create output data path
    if not os.path.exists(raw_data_path):
        subprocess.call(('mkdir', '-p', raw_data_path))
    
    # the iteration we are beginning on. Can be nonzero if resuming a simulation
    start_iter = 0
    # track runtime
    start_time = time.time()
    record_time = time.time()

    data_x = torch.empty(0,2, **tkwargs)
    data_obj = torch.empty(0,2, **tkwargs)

    # create output data file
    if not os.path.exists(averages_file):
        with open(averages_file, 'w') as file:
            line1 = "Iteration,Param1,Param2,Drag,Sideforce,Lift,Stdev Drag,Stdev Sideforce,Stdev Lift,Time"
            file.write(line1)
    else:
        # pull initial params from existing file to allow saving progress and continuing
        with open(averages_file, 'r') as file:
            # get last line in the file
            lines = file.readlines()
            last_line = lines[-1].split(',')
            try:
                start_iter = int(last_line[0]) + 1
                record_time -= float(last_line[9])
                for line in lines:
                    split = line.split(',')
                    if split[0].isnumeric():
                        # add to data
                        data_x = torch.cat([data_x, torch.tensor([[float(split[1]), float(split[2])]], **tkwargs)])
                        # negate drag because botorch maximizes
                        data_obj = torch.cat([data_obj, torch.tensor([[-float(split[3]), -float(split[5])]], **tkwargs)])
                    
                print(f'Resuming on iteration {start_iter}.')
            except:
                print('Found averages file, but unable to pull previous parameters...')

    cur_iter = start_iter
    # create initial sample if not finished yet
    if len(data_x) < initial_sample_size:
        print(f'Need {initial_sample_size-len(data_x)} more points to fill initial sample, creating...')
        initial_points = bayesian_optimization.initial_points(initial_sample_size - len(data_x))
        print(f'Initial sample points: {initial_points}')
        for point in initial_points:
            data_x, data_obj = run_step(cur_iter, point, \
                start_time, record_time, data_x, data_obj, fake_simulation)
            cur_iter += 1

    new_param_batch = torch.empty(0,2,**tkwargs)
    for _ in range(batches):  
        # initialize model and get batch of parameters
        print('\nGetting new parameter batch via Bayesian Optimization...')
        mll, model = bayesian_optimization.initialize_model(data_x, data_obj)
        new_param_batch = bayesian_optimization.optimize_qnehvi_and_get_candidate(model, mll, data_x)
        print(f'{len(new_param_batch)} new parameter sets received.')

        for new_params in new_param_batch:
            # run step for each new parameter set from batch
            data_x, data_obj = run_step(cur_iter, new_params, start_time, \
                record_time, data_x, data_obj, fake_simulation)
            cur_iter += 1

    print('\r\n\r\n----------------------------------')
    print('Finished %i iterations in %fs' %(cur_iter - start_iter + 1,time.time()-start_time))

def run_step(cur_iter, new_params, start_time, record_time, \
    data_x, data_obj, fake_simulation = False):
    """
    Run a single step in the simulation.
    """
    print('\r\n\r\n----------------------------------')
    print('Beginning iteration %i' %(cur_iter,))
    iter_start_time = time.time()

    print(f'Using params: {(float(new_params[0]), float(new_params[1]))}')
    
    if fake_simulation:
        # fake simulation to test simulated annealing
        print('Faking simulation...')
        # fake function which minimzes objective at param1 = 0.5, param2 = -0.25
        average = [1000*(new_params[0]-0.5)**2+400, 0, -800+1000*(new_params[1]+0.25)**2]
        stdev = [0]*3
    else:
        # create new runtime directory
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        # create 3d model from blender cli with params
        print('Creating model...\n')
        subprocess.call(('blender', '-b', '-noaudio', './assets/design_space.blend', \
        '-P', 'export_model.py', '--', str(new_params[0]), str(new_params[1]), model_dst))

        # run simulation in runtime dir
        print('\nRunning simulation...')
        wd = os.getcwd()
        with open(foam_log_path, 'w') as foam_log:
            os.chdir(dst)
            subprocess.call(('sh', './run.sh'), stdout=foam_log)
        os.chdir(wd)
        print('Simulation complete, processing data...')

        # calculate running averages
        average, stdev = running_average.run(avg_window_start, avg_window_end)
        # copy raw data file to save
        path_tuple = (raw_data_path,)+new_params
        shutil.copyfile(running_average.DEFAULT_FILE_PATH, '%s/%f,%f.dat' %path_tuple)

    # print results of this iteration
    print('Drag: %f' %(average[0],))
    print('Sideforce: %f' %(average[1],))
    print('Lift:%f' %(average[2],))
    print('\r\n')

    #print time information
    print('Finished iteration %i' %(cur_iter,))
    iter_end_time = time.time()
    print('Time elapsed this iteration: %fs' %(iter_end_time-iter_start_time,))
    print('Total time elapsed: %fs' %(iter_end_time-start_time,))

    # write data to file
    data_tuple = (cur_iter,) + tuple(new_params) + tuple(average) + tuple(stdev) + (iter_end_time-record_time,)
    with open(averages_file, 'a') as file:
        file.write("\n%i,%f,%f,%f,%f,%f,%f,%f,%f,%f" %data_tuple)

    # add to data
    data_x = torch.cat([data_x, new_params.reshape(1,2)])
    # negate because botorch maximizes by default
    data_obj = torch.cat([data_obj, torch.tensor([[-average[0], -average[2]]], **tkwargs)])
    
    return (data_x, data_obj)

if __name__ == '__main__':
    try:
        batches = int(sys.argv[1])
        initial_sample_size = int(sys.argv[2])
        assert batches > 0
        assert initial_sample_size > 0
        assert batches > initial_sample_size
        print('Using user-input parameters')
    except:
        batches = 25
        initial_sample_size = 10
        print('Invalid parameters, using defaults')
    optimize_target(batches, initial_sample_size, '--fake-sim' in sys.argv)