import shutil
import os
import sys
import subprocess
import running_average
import time

src = './template'
dst = './runtime'

avg_window_start = 450
avg_window_end = 500

averages_file = './data/averages.csv'
raw_data_path = './data/forces'

foam_log_path = './foam_log.txt'

if __name__ == '__main__':
    # get args    
    try:
        iters = int(sys.argv[1])
        target_drag = float(sys.argv[2])
        target_lift = float(sys.argv[3])
        assert iters > 0
        print('Using user-input parameters: ')
    except:
        iters = 1
        target_drag = 420
        target_lift = -350
        print('Invalid parameters, using defaults: ')
    
    print('Iters: %i' %(iters,))
    print('Target Drag: %f' %(target_drag,))
    print('Target Lift: %f' %(target_lift,))

    # create output data path
    if not os.path.exists(raw_data_path):
        subprocess.call(('mkdir', '-p', raw_data_path))
    # create output data file
    if not os.path.exists(averages_file):
        with open(averages_file, 'w') as file:
            file.write("Param1,Param2,Drag,Sideforce,Lift,Stdev Drag,Stdev Sideforce,Stdev Lift")

    start_time = time.time()

    for i in range(iters):  
        print('\r\n\r\n----------------------------------')
        print('Beginning iteration %i' %(i,))
        iter_start_time = time.time()
        # todo: modify params
        params = (0,0)
        print('Using params: %f,%f' %params)
        # create new runtime directory
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        
        print('Running simulation...')
        wd = os.getcwd()
        with open(foam_log_path, 'w') as foam_log:
            os.chdir(dst)
            subprocess.call(('sh', './run.sh'), stdout=foam_log)
        os.chdir(wd)

        print('Simulation complete, processing data...')
        # calculate running averages
        average, stdev = running_average.run(avg_window_start, avg_window_end)
        data_tuple = params + tuple(average) + tuple(stdev)
        with open(averages_file, 'a') as file:
            file.write("\n%f,%f,%f,%f,%f,%f,%f,%f" %data_tuple)
        # copy raw data file to save
        path_tuple = (raw_data_path,)+params
        shutil.copyfile(running_average.DEFAULT_FILE_PATH, '%s/%f,%f.dat' %path_tuple)
        print('Drag: %f' %(average[0],))
        print('Sideforce: %f' %(average[1],))
        print('Lift:%f' %(average[2],))
        print('\r\n')

        #print time information
        print('Finished iteration %i' %(i,))
        iter_end_time = time.time()
        print('Time elapsed this iteration: %fs' %(iter_end_time-iter_start_time,))
        print('Total time elapsed: %fs' %(iter_end_time-start_time,))

    print('\r\n\r\n----------------------------------')
    print('Finished %i iterations in %fs' %(iters,time.time()-start_time))
