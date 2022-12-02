import sys
import numpy as np

# adapted from PSET 5 pareto.py
def pareto_indices(points: np.ndarray) -> np.ndarray:
    '''
    Compute the Pareto indices of a set of 2D points. Minimization is assumed for all properties.
    '''
    # Check input validity
    assert points.ndim == 2 and points.shape[-1] == 2 and points.shape[0] > 0, \
        'The input array must represent a set of 2D points'

    # Sort the points by both properties
    points = points[np.lexsort((points[:,1], points[:,0]))]

    pareto_indices = [0]        # List of indices to Pareto-optimal points (in the sorted array)
    pareto_x = points[0, 0]     # X value of the last Pareto-optimal point
    pareto_y = points[0, 1]     # Y value of the last Pareto-optimal point

    # Traverse the sorted array to figure out Pareto-optimal points
    for i in range(points.shape[0]):

        # Add this point to the Pareto front if it isn't dominated by the last Pareto-optimal point
        if points[i, 0] < pareto_x or points[i, 1] < pareto_y:
            pareto_indices.append(i)

            # Update the last Pareto-optimal point using this point
            pareto_x = points[i, 0]
            pareto_y = points[i, 1]

    # Return the Pareto front
    return pareto_indices

def pareto_front(points: np.ndarray) -> np.ndarray:
    '''
    Compute the Pareto front of a set of 2D points. Minimization is assumed for all properties.
    '''
    indices = pareto_indices(points)
    pareto_front = points[indices]
    return pareto_front

def export_pareto_front(input_path, export_path):
    '''
    Export the pareto front of a file. Assumes the file follows the row format:
    Iteration, Param1, Param2, Drag, Sideforce, Downforce, ...
    '''
    with open(input_path, 'r') as file:
        points = np.empty((0,4))
        for line in file.readlines():
            split = line.split(',')
            # ignore column labels
            if not split[0].isnumeric():
                continue
            points = np.append(points, np.array([[float(split[1]), float(split[2]), float(split[3]), float(split[5])]]), axis=0)
    
    data_points = points[:,2:]
    # Get indices so that the parameters can be included in the output without being part of the pareto front
    # computation
    indices = pareto_indices(data_points)
    pareto_front = points[indices]

    with open(export_path, 'w') as export:
        lines = ['Param1,Param2,Drag,Lift']
        for point in pareto_front:
            lines.append(f'\n{point[0]},{point[1]},{point[2]},{point[3]}')
        export.writelines(lines)

if __name__ == '__main__':
    try:
        input_path = sys.argv[1]
    except:
        input_path = './data/averages.csv'
    try:
        export_path = sys.argv[2]
    except:
        export_path = './data/pareto.csv'
    export_pareto_front(input_path, export_path)
    print(f'Exported pareto front of {input_path} to {export_path}')