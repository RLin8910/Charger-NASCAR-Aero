import re
import sys

DEFAULT_FILE_PATH = './runtime/postProcessing/forces/0/forces.dat'

def get_default_path():
    return DEFAULT_FILE_PATH

def run(start_step = 0, end_step = 1000, file_path=DEFAULT_FILE_PATH):
    data = [[], [], []]
    with open(file_path) as file:
        for line in file.readlines():
            # ignore comments
            if line[0] == '#':
                continue
            # split line into components, ignoring white space and parentheses
            components = tuple(filter(lambda x: x != '', re.split("[ \t\n()]", line)))
            # check if time step is within range
            time_step = int(components[0])
            if time_step < start_step or time_step > end_step:
                continue
            # add to running average
            for i in range(len(data)):
                data[i].append(float(components[i+1]))
    average = [0] * len(data)
    stdev = [0] * len(data)

    for i in range(len(data)):
        average[i] = sum(data[i]) / len(data[i])

    for i in range(len(data)):
        for point in data[i]:
            stdev[i] += (point - average[i])**2
        stdev[i] = (stdev[i] / len(data[i]))**0.5

    return (average, stdev)

if __name__ == '__main__':
    try:
        start_step = int(sys.argv[1])
        end_step = int(sys.argv[2])
        assert start_step >= 0
        assert end_step > start_step
    except:
        start_step = 0
        end_step = 1000
        print("Missing or invalid time step range, using defaults of %s to %s." % (start_step, end_step))

    if len(sys.argv) > 3:
        file_path = sys.argv[3]
    else:
        file_path = DEFAULT_FILE_PATH

    average, stdev = run(start_step, end_step, file_path)
    print('Average: ', average)
    print('Stdev: ', stdev)