surfaceFeatures
blockMesh

decomposePar -copyZero

mpirun -np 6 snappyHexMesh -overwrite -parallel
mpirun -np 6 patchSummary -parallel
mpirun -np 6 potentialFoam -parallel
mpirun -np 6 simpleFoam -parallel

reconstructParMesh -constant
reconstructPar