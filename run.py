import shutil
import os
import sys
import subprocess
import time

import running_average
import simulated_annealing
import config

src = './template'
dst = './runtime'
model_dst = './runtime/constant/geometry/model.obj'

avg_window_start = 450
avg_window_end = 500

averages_file = './data/averages.csv'
raw_data_path = './data/forces'

foam_log_path = './foam_log.txt'

def optimize_target(target_drag, target_lift, step_size, temp, iters, fake_simulation=False):   
    """
    Optimize the model for the target drag and lift values.

    Use `fake_simulation` to avoid actually simulating the model in order to test
    simulated annealing.
    """ 
    print('\nBegin optimizing with parameters: ')
    print('Target Drag: %f' %(target_drag,))
    print('Target Lift: %f' %(target_lift,))
    print('Step Size: %f' %(step_size,))
    print('Temp: %f' %(temp,))
    print('Iters: %i' %(iters,))

    # create output data path
    if not os.path.exists(raw_data_path):
        subprocess.call(('mkdir', '-p', raw_data_path))
    
    # initialize parameters and error
    cur_params = (0,0)
    cur_eval = float('inf')
    # the iteration we are beginning on. Can be nonzero if resuming a simulation
    start_iter = 0

    # create output data file
    if not os.path.exists(averages_file):
        with open(averages_file, 'w') as file:
            line1 = "Iteration,Param1,Param2,Drag,Sideforce,Lift,Stdev Drag,Stdev Sideforce,Stdev Lift,Error"
            line2 = f"\nTarget,--,--,{target_drag},--,{target_lift},--,--,--,0"
            file.writelines((line1,line2))
    else:
        # pull initial params from existing file to allow saving progress and continuing
        with open(averages_file, 'r') as file:
            # get last line in the file
            last_line = file.readlines()[-1].split(',')
            try:
                start_iter = int(last_line[0]) + 1
                cur_params = (float(last_line[1]), float(last_line[2]))
                drag = float(last_line[3])
                lift = float(last_line[4])
                cur_eval = simulated_annealing.objective((target_drag, target_lift), (drag, lift))
                print(f'Resuming with parameters {cur_params} and error {cur_eval} on iteration {start_iter}.')
            except:
                print('Found averages file, but unable to pull previous parameters...')
    
    # track runtime
    start_time = time.time()

    for i in range(start_iter, iters+start_iter):  
        print('\r\n\r\n----------------------------------')
        print('Beginning iteration %i' %(i,))
        iter_start_time = time.time()

        params = tuple(simulated_annealing.get_candidate(cur_params, config.min_bound, config.max_bound, \
            step_size))
        print('Using params: %f,%f' %params)
        
        if fake_simulation:
            # fake simulation to test simulated annealing
            print('Faking simulation...')
            # fake function which minimzes objective at param1 = 0.5, param2 = -0.25
            average = [100*(params[0]-0.5)+target_drag, 0, 100*(params[1]+0.25)+target_lift]
            stdev = [0]*3
        else:
            # create new runtime directory
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

            # create 3d model from blender cli with params
            print('Creating model...\n')
            subprocess.call(('blender', '-b', '-noaudio', './assets/design_space.blend', \
            '-P', 'export_model.py', '--', str(params[0]), str(params[1]), model_dst))

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
            path_tuple = (raw_data_path,)+params
            shutil.copyfile(running_average.DEFAULT_FILE_PATH, '%s/%f,%f.dat' %path_tuple)

        eval = simulated_annealing.objective((target_drag, target_lift), (average[0], average[2]))

        # write data to file
        data_tuple = (i,) + params + tuple(average) + tuple(stdev) + (eval,)
        with open(averages_file, 'a') as file:
                file.write("\n%i,%f,%f,%f,%f,%f,%f,%f,%f,%f" %data_tuple)

        # print results of this iteration
        print('Drag: %f' %(average[0],))
        print('Sideforce: %f' %(average[1],))
        print('Lift:%f' %(average[2],))
        print('Error:%f' %(eval,))
        print('\r\n')

        # determine whether to accept this candidate
        if simulated_annealing.check_accept(cur_eval, eval, i, temp):
            # accept candidate
            cur_eval = eval
            cur_params = params

        #print time information
        print('Finished iteration %i' %(i,))
        iter_end_time = time.time()
        print('Time elapsed this iteration: %fs' %(iter_end_time-iter_start_time,))
        print('Total time elapsed: %fs' %(iter_end_time-start_time,))

    print('\r\n\r\n----------------------------------')
    print('Finished %i iterations in %fs' %(iters,time.time()-start_time))

if __name__ == '__main__':
    # get args    
    try:
        target_drag = float(sys.argv[1])
        target_lift = float(sys.argv[2])
        step_size = float(sys.argv[3])
        temp = float(sys.argv[4])
        iters = int(sys.argv[5])
        assert iters > 0
        print('Using user-input parameters')
    except:
        target_drag = 420
        target_lift = -800
        step_size = 0.05
        temp = 5
        iters = 1000
        print('Invalid parameters, using defaults')
    optimize_target(target_drag, target_lift, step_size, temp, iters, '--fake-sim' in sys.argv)